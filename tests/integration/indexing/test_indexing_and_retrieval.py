from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

import numpy as np
import pytest

from groundnote.config import Settings
from groundnote.documents import DocumentError
from groundnote.domain import DocumentStatus, SupportedFileType
from groundnote.embeddings import (
    DocumentAlreadyIndexedError,
    EmbeddingGenerationError,
    EmbeddingService,
)
from groundnote.retrieval import EmptyQueryError, RetrievalError, SemanticRetrievalService
from groundnote.services import DocumentIndexingService, PreEmbeddingIngestionService
from groundnote.storage import (
    MigrationRunner,
    SQLiteConnectionFactory,
    SQLiteDocumentRepository,
    SQLiteUnitOfWorkFactory,
    SQLiteVectorRepository,
)
from tests.integration.documents.conftest import write_docx, write_text_pdf


class KeywordEmbeddingProvider:
    def __init__(self, *, dimension: int = 1024, fail: bool = False) -> None:
        self.model_alias = "qwen3-embedding-0.6b"
        self.dimension = dimension
        self.loaded = False
        self.fail = fail
        self.calls: list[list[str]] = []

    def load(self) -> None:
        self.loaded = True

    def unload(self) -> None:
        self.loaded = False

    def embed_many(self, texts: Sequence[str], *, batch_size: int = 8) -> object:
        if not self.loaded or self.fail:
            raise RuntimeError("provider unavailable")
        self.calls.append(list(texts))
        vectors = np.vstack([self._embed(text) for text in texts]).astype(np.float32)
        return type("Batch", (), {"vectors": vectors})()

    def embed_one(self, text: str) -> np.ndarray:
        if not self.loaded or self.fail:
            raise RuntimeError("provider unavailable")
        return self._embed(text)

    def _embed(self, text: str) -> np.ndarray:
        lowered = text.lower()
        vector = np.zeros(self.dimension, dtype=np.float32)
        if any(word in lowered for word in ("algebra", "vector", "matrix")):
            vector[0] = 1.0
        elif any(word in lowered for word in ("database", "index", "sorgu", "veritaban")):
            vector[1] = 1.0
        elif any(word in lowered for word in ("function", "maps", "set")):
            vector[2] = 1.0
        else:
            vector[3] = 1.0
        return vector


@pytest.fixture
def initialized_database(tmp_path: Path) -> Path:
    database_path = tmp_path / "groundnote.sqlite3"
    with SQLiteConnectionFactory(database_path).open() as connection:
        MigrationRunner().apply(connection)
    return database_path


def test_phase4_ingestion_to_phase5_indexing_and_retrieval(
    tmp_path: Path,
    initialized_database: Path,
) -> None:
    document_id, provider, settings = _ingest_and_index_text(
        tmp_path,
        initialized_database,
        "Linear algebra studies vectors and matrices.\n\nDatabase indexes speed up queries.",
    )

    with SQLiteConnectionFactory(initialized_database).open() as connection:
        document = SQLiteDocumentRepository(connection).get_by_id(document_id)
        vectors = SQLiteVectorRepository(connection)
        assert document.status == DocumentStatus.INDEXED
        assert document.embedding_model == settings.embedding_model
        assert document.embedding_dimension == 1024
        assert document.embedding_version == settings.embedding_version
        embedded_count = vectors.count_embedded_chunks_for_document(document_id)
        total_count = vectors.count_chunks_for_document(document_id)
        assert embedded_count == total_count
        assert vectors.list_all_embeddings()[0].embedding is not None

    retrieval = SemanticRetrievalService(
        settings=settings,
        connection_factory=SQLiteConnectionFactory(initialized_database),
        embedding_service=EmbeddingService(settings=settings, provider=provider),
    )
    response = retrieval.search("matrix vector algebra", minimum_score=0.0)

    assert response.results
    assert response.results[0].score >= response.results[-1].score
    assert response.results[0].source_filename == "notes.txt"
    assert response.results[0].chunk_index == 0
    assert not hasattr(response, "answer")


def test_indexes_all_supported_formats_with_fake_embeddings(
    tmp_path: Path,
    initialized_database: Path,
) -> None:
    document_dir = tmp_path / "documents"
    document_dir.mkdir()
    settings = Settings(data_directory=tmp_path / "app")
    ingestion = PreEmbeddingIngestionService(
        settings=settings,
        unit_of_work_factory=SQLiteUnitOfWorkFactory(initialized_database),
    )
    files = [
        (write_text_pdf(document_dir / "notes.pdf", ["Linear algebra page."]), "notes.pdf"),
        (write_docx(document_dir / "notes.docx"), "notes.docx"),
        (_write(document_dir / "notes.txt", "Database index text."), "notes.txt"),
        (_write(document_dir / "notes.md", "# Functions\n\nA function maps sets."), "notes.md"),
    ]

    for path, filename in files:
        plan = ingestion.ingest_file(
            path,
            original_filename=filename,
            allowed_directory=document_dir,
        )
        provider = KeywordEmbeddingProvider()
        indexer = DocumentIndexingService(
            settings=settings,
            unit_of_work_factory=SQLiteUnitOfWorkFactory(initialized_database),
            embedding_service=EmbeddingService(settings=settings, provider=provider),
        )
        document_id = plan.chunks[0].document_id or _document_id_for_sha(
            initialized_database,
            plan.sha256,
        )
        indexer.index_document(document_id)

    with SQLiteConnectionFactory(initialized_database).open() as connection:
        assert SQLiteDocumentRepository(connection).count_by_status(DocumentStatus.INDEXED) == 4


def test_indexing_failure_rolls_back_and_document_is_not_searchable(
    tmp_path: Path,
    initialized_database: Path,
) -> None:
    document_id, _, settings = _ingest_text(
        tmp_path,
        initialized_database,
        "Linear algebra studies vectors.",
    )
    provider = KeywordEmbeddingProvider(fail=True)
    indexer = DocumentIndexingService(
        settings=settings,
        unit_of_work_factory=SQLiteUnitOfWorkFactory(initialized_database),
        embedding_service=EmbeddingService(settings=settings, provider=provider),
    )

    with pytest.raises(EmbeddingGenerationError):
        indexer.index_document(document_id)

    with SQLiteConnectionFactory(initialized_database).open() as connection:
        document = SQLiteDocumentRepository(connection).get_by_id(document_id)
        assert document.status == DocumentStatus.PENDING_EMBEDDING
        embedded_count = SQLiteVectorRepository(connection).count_embedded_chunks_for_document(
            document_id
        )
        assert embedded_count == 0


def test_already_indexed_rejected_and_force_reindex_preserves_chunks(
    tmp_path: Path,
    initialized_database: Path,
) -> None:
    document_id, provider, settings = _ingest_and_index_text(
        tmp_path,
        initialized_database,
        "Database index text.",
    )
    indexer = DocumentIndexingService(
        settings=settings,
        unit_of_work_factory=SQLiteUnitOfWorkFactory(initialized_database),
        embedding_service=EmbeddingService(settings=settings, provider=provider),
    )

    with pytest.raises(DocumentAlreadyIndexedError):
        indexer.index_document(document_id)

    before = _chunk_count(initialized_database, document_id)
    indexer.index_document(document_id, force_reindex=True)
    after = _chunk_count(initialized_database, document_id)

    assert before == after


def test_retrieval_filters_and_exclusions(tmp_path: Path, initialized_database: Path) -> None:
    indexed_id, provider, settings = _ingest_and_index_text(
        tmp_path,
        initialized_database,
        "Database indexes can speed up queries.",
    )
    pending_id, _, _ = _ingest_text(
        tmp_path,
        initialized_database,
        "Linear algebra pending text.",
        filename="pending.txt",
    )
    retrieval = SemanticRetrievalService(
        settings=settings,
        connection_factory=SQLiteConnectionFactory(initialized_database),
        embedding_service=EmbeddingService(settings=settings, provider=provider),
    )

    response = retrieval.search(
        "database index",
        document_ids=[indexed_id],
        file_types=[SupportedFileType.TXT],
        minimum_score=0.0,
    )
    empty = retrieval.search("database index", document_ids=[pending_id], minimum_score=0.0)

    assert response.returned_count == 1
    assert response.results[0].document_id == indexed_id
    assert empty.returned_count == 0
    with pytest.raises(EmptyQueryError):
        retrieval.search("   ")


def test_malformed_embedding_blob_fails_safely(tmp_path: Path, initialized_database: Path) -> None:
    document_id, provider, settings = _ingest_and_index_text(
        tmp_path,
        initialized_database,
        "Database indexes can speed up queries.",
    )
    with SQLiteConnectionFactory(initialized_database).open() as connection:
        chunk = SQLiteVectorRepository(connection).list_for_document(document_id)[0]
        connection.execute(
            "UPDATE document_chunks SET embedding = ? WHERE id = ?",
            (b"bad", chunk.id),
        )
    retrieval = SemanticRetrievalService(
        settings=settings,
        connection_factory=SQLiteConnectionFactory(initialized_database),
        embedding_service=EmbeddingService(settings=settings, provider=provider),
    )

    with pytest.raises(RetrievalError):
        retrieval.search("database index")


def _ingest_and_index_text(
    tmp_path: Path,
    database_path: Path,
    text: str,
) -> tuple[str, KeywordEmbeddingProvider, Settings]:
    document_id, provider, settings = _ingest_text(tmp_path, database_path, text)
    indexer = DocumentIndexingService(
        settings=settings,
        unit_of_work_factory=SQLiteUnitOfWorkFactory(database_path),
        embedding_service=EmbeddingService(settings=settings, provider=provider),
    )
    indexer.index_document(document_id)
    return document_id, provider, settings


def _ingest_text(
    tmp_path: Path,
    database_path: Path,
    text: str,
    *,
    filename: str = "notes.txt",
) -> tuple[str, KeywordEmbeddingProvider, Settings]:
    document_dir = tmp_path / f"documents-{filename}"
    document_dir.mkdir()
    path = _write(document_dir / filename, text)
    settings = Settings(data_directory=tmp_path / "app")
    ingestion = PreEmbeddingIngestionService(
        settings=settings,
        unit_of_work_factory=SQLiteUnitOfWorkFactory(database_path),
    )
    plan = ingestion.ingest_file(path, original_filename=filename, allowed_directory=document_dir)
    document_id = _document_id_for_sha(database_path, plan.sha256)
    return document_id, KeywordEmbeddingProvider(), settings


def _document_id_for_sha(database_path: Path, sha256: str) -> str:
    with SQLiteConnectionFactory(database_path).open() as connection:
        document = SQLiteDocumentRepository(connection).get_by_sha256(sha256)
        if document is None:
            raise DocumentError("Document fixture was not persisted.")
        return document.id


def _chunk_count(database_path: Path, document_id: str) -> int:
    with SQLiteConnectionFactory(database_path).open() as connection:
        return SQLiteVectorRepository(connection).count_chunks_for_document(document_id)


def _write(path: Path, text: str) -> Path:
    path.write_text(text, encoding="utf-8")
    return path
