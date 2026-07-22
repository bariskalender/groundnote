from __future__ import annotations

import sqlite3
from datetime import UTC, datetime
from pathlib import Path

import pytest

from groundnote.ai.fakes import FakeChatProvider, FakeEmbeddingProvider
from groundnote.bootstrap import initialize_application
from groundnote.config import Settings
from groundnote.domain import Document, DocumentStatus, SupportedFileType
from groundnote.embeddings import IndexingError
from groundnote.storage import (
    SQLiteConnectionFactory,
    SQLiteDocumentRepository,
    SQLiteVectorRepository,
    StorageError,
)
from groundnote.ui import build_application_context


def _settings(tmp_path: Path) -> Settings:
    return Settings(
        data_directory=tmp_path / "app",
        embedding_dimension=4,
        embedding_model="fake-embedding",
        embedding_version="fake-v1",
        chat_model="fake-chat",
        rag_minimum_score=-1.0,
        chunk_target_characters=60,
        chunk_maximum_characters=80,
        chunk_overlap_characters=0,
        chunk_minimum_characters=20,
    )


def _context(settings: Settings):  # type: ignore[no-untyped-def]
    return build_application_context(
        settings,
        embedding_provider=FakeEmbeddingProvider(dimension=4),
        chat_provider=FakeChatProvider(),
    )


def test_bootstrap_recovers_interrupted_indexing_idempotently_and_allows_retry(
    tmp_path: Path,
) -> None:
    settings = _settings(tmp_path)
    context = _context(settings)
    upload = context.document_workflow.process_and_index(
        original_filename="interrupted.txt",
        data=(
            b"First recoverable indexing paragraph with enough detail.\n\n"
            b"Second recoverable indexing paragraph with more detail.\n\n"
            b"Third recoverable indexing paragraph for partial state."
        ),
    )
    document_id = upload.document.document_id
    assert settings.database_path is not None
    with sqlite3.connect(settings.database_path) as connection:
        connection.execute(
            "UPDATE documents SET status = 'indexing', indexed_at = NULL WHERE id = ?",
            (document_id,),
        )
        connection.execute(
            """
            UPDATE document_chunks
            SET embedding = NULL,
                embedding_dimension = NULL,
                embedding_dtype = NULL,
                embedding_model = NULL,
                embedding_version = NULL,
                embedded_at = NULL
            WHERE document_id = ? AND chunk_index = 0
            """,
            (document_id,),
        )
        connection.commit()

    initialize_application(settings)
    initialize_application(settings)

    with SQLiteConnectionFactory(settings.database_path).open() as connection:
        document = SQLiteDocumentRepository(connection).get_by_id(document_id)
        assert document.status is DocumentStatus.FAILED
        assert document.indexed_at is None
        assert document.embedding_model is None
        assert (
            connection.execute(
                "SELECT COUNT(*) FROM document_chunks WHERE document_id = ?",
                (document_id,),
            ).fetchone()[0]
            > 0
        )
        assert (
            connection.execute(
                "SELECT COUNT(*) FROM document_chunks "
                "WHERE document_id = ? AND embedding IS NOT NULL",
                (document_id,),
            ).fetchone()[0]
            == 0
        )
        assert (
            connection.execute(
                "SELECT COUNT(*) FROM document_chunks_fts WHERE document_id = ?",
                (document_id,),
            ).fetchone()[0]
            == 0
        )

    retried = context.document_workflow.reindex_document(document_id)
    assert retried.status is DocumentStatus.INDEXED
    assert retried.chunk_count == retried.embedded_chunk_count > 0


def test_incomplete_index_is_never_ready_or_searchable_on_rerun(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    context = _context(settings)
    upload = context.document_workflow.process_and_index(
        original_filename="incomplete.txt",
        data=b"Incomplete index evidence must not be retrieved.",
    )
    document_id = upload.document.document_id
    assert settings.database_path is not None
    with sqlite3.connect(settings.database_path) as connection:
        connection.execute(
            "DELETE FROM document_chunks_fts WHERE document_id = ?",
            (document_id,),
        )
        connection.commit()

    retrieval = context.retrieval_service.search("incomplete index", minimum_score=-1.0)
    summary = context.document_workflow.get_document(document_id)
    indexed = context.document_workflow.indexed_documents()

    assert summary.status is DocumentStatus.FAILED
    assert indexed == []
    assert retrieval.results == []


def test_recovery_does_not_modify_unrelated_complete_document(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    context = _context(settings)
    interrupted = context.document_workflow.process_and_index(
        original_filename="interrupted.txt",
        data=b"Interrupted fixture.",
    )
    ready = context.document_workflow.process_and_index(
        original_filename="ready.txt",
        data=b"Unrelated complete fixture.",
    )
    assert settings.database_path is not None
    with sqlite3.connect(settings.database_path) as connection:
        connection.execute(
            "UPDATE documents SET status = 'indexing' WHERE id = ?",
            (interrupted.document.document_id,),
        )
        connection.commit()

    initialize_application(settings)

    documents = {item.document_id: item for item in context.document_workflow.list_documents()}
    assert documents[interrupted.document.document_id].status is DocumentStatus.FAILED
    assert documents[ready.document.document_id].status is DocumentStatus.INDEXED


def test_bootstrap_recovers_waiting_document_and_reindex_reuses_committed_chunks(
    tmp_path: Path,
) -> None:
    settings = _settings(tmp_path)
    context = _context(settings)
    assert settings.document_directory is not None
    source = settings.document_directory / "waiting.txt"
    source.write_text("Committed chunks remain available for a safe retry.", encoding="utf-8")
    plan = context.ingestion_service.ingest_file(
        source,
        original_filename=source.name,
        allowed_directory=settings.document_directory,
    )
    document_id = plan.chunks[0].document_id
    assert document_id is not None

    initialize_application(settings)

    interrupted = context.document_workflow.get_document(document_id)
    assert interrupted.status is DocumentStatus.FAILED
    assert interrupted.chunk_count > 0
    assert interrupted.embedded_chunk_count == 0
    assert source.exists()
    retried = context.document_workflow.reindex_document(document_id)
    assert retried.status is DocumentStatus.INDEXED
    assert retried.chunk_count == retried.embedded_chunk_count
    assert source.exists()


def test_bootstrap_marks_document_row_without_chunks_retry_required(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    dependencies = initialize_application(settings)
    now = datetime.now(UTC)
    document = Document(
        id="row-only",
        original_filename="row-only.txt",
        stored_filename="row-only.txt",
        file_type=SupportedFileType.TXT,
        sha256="a" * 64,
        file_size_bytes=10,
        status=DocumentStatus.PENDING,
        created_at=now,
        updated_at=now,
    )
    with dependencies.unit_of_work_factory() as unit_of_work:
        assert unit_of_work.documents is not None
        unit_of_work.documents.add(document)
        unit_of_work.commit()

    initialize_application(settings)

    with dependencies.unit_of_work_factory() as unit_of_work:
        assert unit_of_work.documents is not None
        recovered = unit_of_work.documents.get_by_id(document.id)
        assert recovered.status is DocumentStatus.FAILED
        assert recovered.indexed_at is None


def test_fts_write_failure_leaves_document_retryable_and_cleans_partial_data(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings = _settings(tmp_path)
    context = _context(settings)
    assert settings.document_directory is not None
    source = settings.document_directory / "fts-failure.txt"
    source.write_text("FTS failure fixture with searchable local text.", encoding="utf-8")
    plan = context.ingestion_service.ingest_file(
        source,
        original_filename=source.name,
        allowed_directory=settings.document_directory,
    )
    document_id = plan.chunks[0].document_id
    assert document_id is not None

    def fail_fts_sync(self: SQLiteVectorRepository, chunk_ids: list[str]) -> None:
        raise sqlite3.OperationalError("synthetic FTS failure")

    monkeypatch.setattr(SQLiteVectorRepository, "_sync_fts_rows_for_chunk_ids", fail_fts_sync)

    with pytest.raises(StorageError):
        context.indexing_service.index_document(document_id)

    failed = context.document_workflow.get_document(document_id)
    assert failed.status is DocumentStatus.FAILED
    assert failed.embedded_chunk_count == 0
    assert settings.database_path is not None
    with sqlite3.connect(settings.database_path) as connection:
        assert (
            connection.execute(
                "SELECT COUNT(*) FROM document_chunks_fts WHERE document_id = ?",
                (document_id,),
            ).fetchone()[0]
            == 0
        )


def test_final_integrity_check_rejects_silently_missing_fts_rows(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings = _settings(tmp_path)
    context = _context(settings)
    assert settings.document_directory is not None
    source = settings.document_directory / "missing-fts.txt"
    source.write_text("Missing FTS rows must prevent Ready status.", encoding="utf-8")
    plan = context.ingestion_service.ingest_file(
        source,
        original_filename=source.name,
        allowed_directory=settings.document_directory,
    )
    document_id = plan.chunks[0].document_id
    assert document_id is not None
    monkeypatch.setattr(
        SQLiteVectorRepository,
        "_sync_fts_rows_for_chunk_ids",
        lambda self, chunk_ids: None,
    )

    with pytest.raises(IndexingError):
        context.indexing_service.index_document(document_id)

    failed = context.document_workflow.get_document(document_id)
    assert failed.status is DocumentStatus.FAILED
    assert failed.embedded_chunk_count == 0
