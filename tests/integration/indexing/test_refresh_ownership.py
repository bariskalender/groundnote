from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path
from threading import Event, Thread

import pytest

from groundnote.ai.fakes import FakeChatProvider, FakeEmbeddingProvider
from groundnote.ai.models import EmbeddingBatchResult
from groundnote.config import Settings
from groundnote.domain import DocumentStatus
from groundnote.services import IndexingOperationActiveError
from groundnote.ui import build_application_context


class BlockingEmbeddingProvider(FakeEmbeddingProvider):
    def __init__(self, started: Event, release: Event) -> None:
        super().__init__(dimension=4)
        self.started = started
        self.release = release

    def embed_many(
        self,
        texts: Sequence[str],
        *,
        batch_size: int = 8,
    ) -> EmbeddingBatchResult:
        self.started.set()
        if not self.release.wait(timeout=10):
            raise TimeoutError("Synthetic refresh test did not release embedding.")
        return super().embed_many(texts, batch_size=batch_size)


class BlockingFailingEmbeddingProvider(BlockingEmbeddingProvider):
    def embed_many(
        self,
        texts: Sequence[str],
        *,
        batch_size: int = 8,
    ) -> EmbeddingBatchResult:
        super().embed_many(texts, batch_size=batch_size)
        raise RuntimeError("Synthetic embedding failure.")


def _settings(tmp_path: Path) -> Settings:
    return Settings(
        data_directory=tmp_path / "app",
        embedding_dimension=4,
        embedding_model="fake-embedding",
        embedding_version="fake-refresh-v1",
        chat_model="fake-chat",
        keep_models_loaded=False,
    )


def test_refresh_like_context_does_not_recover_genuinely_active_indexing(
    tmp_path: Path,
) -> None:
    settings = _settings(tmp_path)
    started = Event()
    release = Event()
    provider = BlockingEmbeddingProvider(started, release)
    original = build_application_context(
        settings,
        embedding_provider=provider,
        chat_provider=FakeChatProvider(),
    )
    failures: list[BaseException] = []

    def index_document() -> None:
        try:
            original.document_workflow.process_and_index(
                original_filename="refresh fixture.txt",
                data=b"A controlled document remains unavailable until embedding commits.",
            )
        except BaseException as exc:
            failures.append(exc)

    worker = Thread(target=index_document, name="groundnote-refresh-test")
    worker.start()
    assert started.wait(timeout=10)
    try:
        refreshed = build_application_context(
            settings,
            embedding_provider=FakeEmbeddingProvider(dimension=4),
            chat_provider=FakeChatProvider(),
        )
        documents = refreshed.document_workflow.list_documents()

        assert len(documents) == 1
        assert documents[0].status is DocumentStatus.INDEXING
        document_id = documents[0].document_id
        chunk_count = documents[0].chunk_count
        assert refreshed.document_workflow.indexed_documents() == []
        search = refreshed.retrieval_service.search("controlled evidence")
        assert search.results == []
        assert search.warnings == ["indexing_active"]
        assert settings.document_directory is not None
        managed_files_before = sorted(settings.document_directory.iterdir())
        with pytest.raises(IndexingOperationActiveError):
            refreshed.document_workflow.process_and_index(
                original_filename="blocked second.txt",
                data=b"A second upload must not enter the active pipeline.",
            )
        assert sorted(settings.document_directory.iterdir()) == managed_files_before
        with pytest.raises(IndexingOperationActiveError):
            refreshed.indexing_service.index_document(document_id)
    finally:
        release.set()
        worker.join(timeout=10)

    assert not worker.is_alive()
    assert failures == []
    ready = refreshed.document_workflow.list_documents()
    assert ready[0].status is DocumentStatus.INDEXED
    assert ready[0].embedded_chunk_count == ready[0].chunk_count
    assert ready[0].chunk_count == chunk_count
    assert refreshed.indexing_registry.is_active() is False
    assert original.embedding_service.is_loaded is False


def test_refresh_like_context_preserves_active_failure_then_shows_retryable(
    tmp_path: Path,
) -> None:
    settings = _settings(tmp_path)
    started = Event()
    release = Event()
    original = build_application_context(
        settings,
        embedding_provider=BlockingFailingEmbeddingProvider(started, release),
        chat_provider=FakeChatProvider(),
    )
    failures: list[BaseException] = []

    def index_document() -> None:
        try:
            original.document_workflow.process_and_index(
                original_filename="failure fixture.txt",
                data=b"A failed embedding must remain retryable after a refresh.",
            )
        except BaseException as exc:
            failures.append(exc)

    worker = Thread(target=index_document, name="groundnote-refresh-failure-test")
    worker.start()
    assert started.wait(timeout=10)
    refreshed = build_application_context(
        settings,
        embedding_provider=FakeEmbeddingProvider(dimension=4),
        chat_provider=FakeChatProvider(),
    )
    try:
        assert refreshed.document_workflow.list_documents()[0].status is DocumentStatus.INDEXING
    finally:
        release.set()
        worker.join(timeout=10)

    assert not worker.is_alive()
    assert len(failures) == 1
    documents = refreshed.document_workflow.list_documents()
    assert documents[0].status is DocumentStatus.FAILED
    assert documents[0].embedded_chunk_count == 0
    assert refreshed.document_workflow.indexed_documents() == []
    assert refreshed.indexing_registry.is_active() is False
    assert original.embedding_service.is_loaded is False


def test_refresh_during_owned_pre_embedding_state_is_not_recovered_until_restart(
    tmp_path: Path,
) -> None:
    settings = _settings(tmp_path)
    original = build_application_context(
        settings,
        embedding_provider=FakeEmbeddingProvider(dimension=4),
        chat_provider=FakeChatProvider(),
    )
    assert settings.document_directory is not None
    stored = settings.document_directory / "owned-pending.txt"
    stored.write_text("An owned pending record is still part of a live upload.", encoding="utf-8")
    pipeline_token = original.indexing_registry.claim_pipeline()
    try:
        original.ingestion_service.ingest_file(
            stored,
            original_filename="owned pending.txt",
            allowed_directory=settings.document_directory,
        )
        refreshed = build_application_context(
            settings,
            embedding_provider=FakeEmbeddingProvider(dimension=4),
            chat_provider=FakeChatProvider(),
        )
        pending = refreshed.document_workflow.list_documents()
        assert pending[0].status is DocumentStatus.PENDING_EMBEDDING
        assert refreshed.document_workflow.indexed_documents() == []
    finally:
        original.indexing_registry.release_pipeline(pipeline_token)

    restarted = build_application_context(
        settings,
        embedding_provider=FakeEmbeddingProvider(dimension=4),
        chat_provider=FakeChatProvider(),
    )
    assert restarted.document_workflow.list_documents()[0].status is DocumentStatus.FAILED
