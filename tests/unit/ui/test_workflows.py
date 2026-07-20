from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

import pytest

from groundnote.ai.fakes import FakeChatProvider, FakeEmbeddingProvider
from groundnote.ai.models import EmbeddingBatchResult
from groundnote.config import Settings
from groundnote.documents import UnsupportedFileTypeError
from groundnote.domain import DocumentStatus, SupportedFileType
from groundnote.embeddings import EmbeddingGenerationError, EmbeddingModelLoadError
from groundnote.ui import build_application_context
from groundnote.ui.errors import NoFileSelectedError
from groundnote.ui.models import UploadOutcomeKind, UploadStage


class FailingEmbeddingProvider(FakeEmbeddingProvider):
    def embed_many(
        self,
        texts: Sequence[str],
        *,
        batch_size: int = 8,
    ) -> EmbeddingBatchResult:
        raise RuntimeError("synthetic private provider failure")


class LoadFailEmbeddingProvider(FakeEmbeddingProvider):
    def load(self) -> None:
        raise RuntimeError("synthetic private model load failure")


class CountingEmbeddingProvider(FakeEmbeddingProvider):
    def __init__(self, dimension: int = 4) -> None:
        super().__init__(dimension=dimension)
        self.load_calls = 0

    def load(self) -> None:
        self.load_calls += 1
        super().load()


def _settings(tmp_path: Path) -> Settings:
    return Settings(
        data_directory=tmp_path / "app",
        embedding_dimension=4,
        embedding_model="fake-embedding",
        embedding_version="fake-v1",
        chat_model="fake-chat",
        rag_minimum_score=-1.0,
    )


def test_upload_orchestration_indexes_and_never_retains_bytes(tmp_path: Path) -> None:
    context = build_application_context(
        _settings(tmp_path),
        embedding_provider=FakeEmbeddingProvider(dimension=4),
        chat_provider=FakeChatProvider(),
    )
    stages: list[UploadStage] = []

    outcome = context.document_workflow.process_and_index(
        original_filename="notes.md",
        data=b"# Vector Search\n\nEmbeddings support local semantic search.",
        on_stage=stages.append,
    )

    assert outcome.kind is UploadOutcomeKind.SUCCESS
    assert outcome.document.status is DocumentStatus.INDEXED
    assert outcome.document.chunk_count == outcome.document.embedded_chunk_count == 1
    assert stages == [
        UploadStage.SAVING,
        UploadStage.PROCESSING,
        UploadStage.INDEXING,
        UploadStage.FINALIZING,
        UploadStage.READY,
    ]
    assert not hasattr(outcome, "data")
    with context.unit_of_work_factory() as unit_of_work:
        assert unit_of_work.documents is not None
        stored = unit_of_work.documents.get_by_id(outcome.document.document_id)
    assert context.settings.document_directory is not None
    assert (context.settings.document_directory / stored.stored_filename).is_file()


def test_duplicate_upload_does_not_index_or_create_another_file(tmp_path: Path) -> None:
    embedding = CountingEmbeddingProvider(dimension=4)
    context = build_application_context(
        _settings(tmp_path),
        embedding_provider=embedding,
        chat_provider=FakeChatProvider(),
    )
    data = b"# Duplicate\n\nIdentical content."
    first = context.document_workflow.process_and_index(original_filename="notes.md", data=data)

    duplicate = context.document_workflow.process_and_index(
        original_filename="renamed.md",
        data=data,
    )

    assert duplicate.kind is UploadOutcomeKind.DUPLICATE
    assert duplicate.document.document_id == first.document.document_id
    assert len(context.document_workflow.list_documents()) == 1
    assert context.settings.document_directory is not None
    assert len(list(context.settings.document_directory.iterdir())) == 1
    assert embedding.loaded is True
    assert embedding.load_calls == 1


def test_multiple_uploads_reuse_warm_embedding_model(tmp_path: Path) -> None:
    embedding = CountingEmbeddingProvider(dimension=4)
    context = build_application_context(
        _settings(tmp_path),
        embedding_provider=embedding,
        chat_provider=FakeChatProvider(),
    )

    context.document_workflow.process_and_index(
        original_filename="first.txt",
        data=b"The first local note is indexed.",
    )
    context.document_workflow.process_and_index(
        original_filename="second.txt",
        data=b"The second local note is indexed.",
    )

    assert embedding.loaded is True
    assert embedding.load_calls == 1
    assert len(context.document_workflow.indexed_documents()) == 2


def test_no_file_and_ingestion_failure_stop_before_indexing_and_cleanup(tmp_path: Path) -> None:
    embedding = FakeEmbeddingProvider(dimension=4)
    context = build_application_context(
        _settings(tmp_path),
        embedding_provider=embedding,
        chat_provider=FakeChatProvider(),
    )

    with pytest.raises(NoFileSelectedError):
        context.document_workflow.process_and_index(original_filename="", data=b"value")
    with pytest.raises(UnsupportedFileTypeError):
        context.document_workflow.process_and_index(
            original_filename="corrupt.pdf",
            data=b"not a pdf",
        )

    assert context.document_workflow.list_documents() == []
    assert embedding.loaded is False
    assert context.settings.document_directory is not None
    assert list(context.settings.document_directory.iterdir()) == []


def test_indexing_failure_is_non_searchable_and_preserves_safe_status(tmp_path: Path) -> None:
    context = build_application_context(
        _settings(tmp_path),
        embedding_provider=FailingEmbeddingProvider(dimension=4),
        chat_provider=FakeChatProvider(),
    )

    with pytest.raises(EmbeddingGenerationError):
        context.document_workflow.process_and_index(
            original_filename="notes.txt",
            data=b"A valid local study note.",
        )

    documents = context.document_workflow.list_documents()
    assert len(documents) == 1
    assert documents[0].status is DocumentStatus.FAILED
    assert documents[0].embedded_chunk_count == 0
    assert context.document_workflow.indexed_documents() == []


def test_embedding_model_load_failure_marks_document_failed_and_retryable(tmp_path: Path) -> None:
    context = build_application_context(
        _settings(tmp_path),
        embedding_provider=LoadFailEmbeddingProvider(dimension=4),
        chat_provider=FakeChatProvider(),
    )

    with pytest.raises(EmbeddingModelLoadError):
        context.document_workflow.process_and_index(
            original_filename="notes.txt",
            data=b"A valid note whose model load fails.",
        )

    document = context.document_workflow.list_documents()[0]
    assert document.status is DocumentStatus.FAILED
    assert document.embedded_chunk_count == 0


def test_question_orchestration_forwards_filters_and_returns_one_latest_answer(
    tmp_path: Path,
) -> None:
    chat = FakeChatProvider(responses=["Grounded vector answer. [S1]"])
    context = build_application_context(
        _settings(tmp_path),
        embedding_provider=FakeEmbeddingProvider(dimension=4),
        chat_provider=chat,
    )
    upload = context.document_workflow.process_and_index(
        original_filename="notes.md",
        data=b"# Vector Search\n\nVector search uses embeddings.",
    )

    outcome = context.question_workflow.answer(
        "How does vector search work?",
        document_ids=[upload.document.document_id],
        file_types=[SupportedFileType.MARKDOWN],
    )

    assert outcome.answer.grounded is True
    assert outcome.answer.citations[0].source_filename == "notes.md"
    assert outcome.document_ids == (upload.document.document_id,)
    assert chat.calls == 1
    assert chat.loaded is True


def test_question_without_indexed_document_fails_before_provider_call(tmp_path: Path) -> None:
    chat = FakeChatProvider()
    context = build_application_context(
        _settings(tmp_path),
        embedding_provider=FakeEmbeddingProvider(dimension=4),
        chat_provider=chat,
    )

    outcome = context.question_workflow.answer("What is in my notes?")

    assert outcome.answer.insufficient_evidence is True
    assert "Please upload a document first" in outcome.answer.answer
    assert chat.calls == 0


def test_short_unclear_question_skips_documents_and_provider_call(tmp_path: Path) -> None:
    chat = FakeChatProvider()
    context = build_application_context(
        _settings(tmp_path),
        embedding_provider=FakeEmbeddingProvider(dimension=4),
        chat_provider=chat,
    )

    outcome = context.question_workflow.answer("A", response_language="tr")

    assert "daha açık" in outcome.answer.answer
    assert outcome.answer.model == "deterministic-router"
    assert chat.calls == 0


def test_processing_documents_without_ready_document_returns_friendly_message(
    tmp_path: Path,
) -> None:
    context = build_application_context(
        _settings(tmp_path),
        embedding_provider=FakeEmbeddingProvider(dimension=4),
        chat_provider=FakeChatProvider(),
    )
    assert context.settings.document_directory is not None
    source = context.settings.document_directory / "pending.txt"
    source.write_bytes(b"This document has been parsed but not embedded yet.")
    context.ingestion_service.ingest_file(
        source,
        original_filename="pending.txt",
        allowed_directory=context.settings.document_directory,
    )

    outcome = context.question_workflow.answer("What is in the note?")

    assert outcome.answer.insufficient_evidence is True
    assert "Documents are being prepared" in outcome.answer.answer


def test_one_ready_document_allows_question_while_another_is_processing(tmp_path: Path) -> None:
    chat = FakeChatProvider(responses=["The ready note is searchable. [S1]"])
    context = build_application_context(
        _settings(tmp_path),
        embedding_provider=FakeEmbeddingProvider(dimension=4),
        chat_provider=chat,
    )
    ready = context.document_workflow.process_and_index(
        original_filename="ready.txt",
        data=b"The ready note is searchable.",
    )
    assert context.settings.document_directory is not None
    source = context.settings.document_directory / "pending.txt"
    source.write_bytes(b"This second document is still pending.")
    context.ingestion_service.ingest_file(
        source,
        original_filename="pending.txt",
        allowed_directory=context.settings.document_directory,
    )

    outcome = context.question_workflow.answer(
        "What is searchable?",
        document_ids=[ready.document.document_id],
    )

    assert outcome.answer.grounded is True
    assert chat.calls == 1


def test_insufficient_evidence_returns_no_citations_and_skips_chat(tmp_path: Path) -> None:
    chat = FakeChatProvider()
    context = build_application_context(
        _settings(tmp_path),
        embedding_provider=FakeEmbeddingProvider(dimension=4),
        chat_provider=chat,
    )
    context.document_workflow.process_and_index(
        original_filename="notes.txt",
        data=b"Local semantic retrieval notes.",
    )

    outcome = context.question_workflow.answer(
        "Unrelated astronomical observation?",
        minimum_score=1.0,
    )

    assert outcome.answer.insufficient_evidence is True
    assert outcome.answer.citations == []
    assert chat.calls == 0
