from __future__ import annotations

import hashlib
from collections.abc import Sequence
from pathlib import Path

import pytest

from groundnote.ai.fakes import FakeChatProvider, FakeEmbeddingProvider
from groundnote.ai.models import EmbeddingBatchResult
from groundnote.config import Settings
from groundnote.documents.parsers.text import TextParser
from groundnote.domain import DocumentStatus
from groundnote.embeddings import EmbeddingGenerationError
from groundnote.performance import IndexingStage
from groundnote.ui import build_application_context


class CountingEmbeddingProvider(FakeEmbeddingProvider):
    def __init__(self) -> None:
        super().__init__(dimension=4)
        self.batch_sizes: list[int] = []

    def embed_many(
        self,
        texts: Sequence[str],
        *,
        batch_size: int = 8,
    ) -> EmbeddingBatchResult:
        self.batch_sizes.append(len(texts))
        return super().embed_many(texts, batch_size=batch_size)


class FailLaterBatchEmbeddingProvider(CountingEmbeddingProvider):
    def embed_many(
        self,
        texts: Sequence[str],
        *,
        batch_size: int = 8,
    ) -> EmbeddingBatchResult:
        if self.batch_sizes:
            raise RuntimeError("synthetic later-batch failure")
        return super().embed_many(texts, batch_size=batch_size)


class CountingChunker:
    def __init__(self, delegate: object) -> None:
        self.delegate = delegate
        self.calls = 0

    def chunk(self, document, settings):
        self.calls += 1
        return self.delegate.chunk(document, settings)


def _settings(tmp_path: Path) -> Settings:
    return Settings(
        data_directory=tmp_path / "app",
        embedding_dimension=4,
        embedding_model="fake-embedding",
        embedding_version="fake-performance-v1",
        embedding_batch_size=2,
        chunk_target_characters=180,
        chunk_maximum_characters=240,
        chunk_minimum_characters=20,
        chunk_overlap_characters=20,
        chat_model="fake-chat",
        keep_models_loaded=False,
    )


def test_one_upload_hashes_parses_chunks_and_batches_once(
    tmp_path: Path,
    monkeypatch,
) -> None:
    parse_calls = 0
    original_parse = TextParser.parse

    def count_parse(self, *args, **kwargs):
        nonlocal parse_calls
        parse_calls += 1
        return original_parse(self, *args, **kwargs)

    def unexpected_file_hash(_path: Path) -> str:
        raise AssertionError("the UI-provided content hash should be reused")

    monkeypatch.setattr(TextParser, "parse", count_parse)
    monkeypatch.setattr("groundnote.documents.service.calculate_sha256", unexpected_file_hash)
    embedding = CountingEmbeddingProvider()
    context = build_application_context(
        _settings(tmp_path),
        embedding_provider=embedding,
        chat_provider=FakeChatProvider(),
    )
    counting_chunker = CountingChunker(context.ingestion_service.chunker)
    context.ingestion_service.chunker = counting_chunker
    data = ("Local indexing evidence and bounded batch behavior. " * 80).encode()

    outcome = context.document_workflow.process_and_index(
        original_filename="performance-fixture.txt",
        data=data,
        precomputed_sha256=hashlib.sha256(data).hexdigest(),
    )

    assert parse_calls == 1
    assert counting_chunker.calls == 1
    assert outcome.diagnostics is not None
    assert outcome.diagnostics.hash_reused is True
    assert outcome.diagnostics.chunk_count == outcome.document.chunk_count
    assert outcome.diagnostics.embedding_batch_count == len(embedding.batch_sizes)
    assert all(size <= 2 for size in embedding.batch_sizes)
    assert sum(embedding.batch_sizes) == outcome.document.chunk_count


def test_completed_indexing_reports_every_required_stage(tmp_path: Path) -> None:
    context = build_application_context(
        _settings(tmp_path),
        embedding_provider=FakeEmbeddingProvider(dimension=4),
        chat_provider=FakeChatProvider(),
    )

    outcome = context.document_workflow.process_and_index(
        original_filename="timings.txt",
        data=b"A safe local fixture for indexing stage diagnostics.",
    )

    assert outcome.diagnostics is not None
    stages = outcome.diagnostics.stage_durations_ms
    required = {
        stage.value
        for stage in (
            IndexingStage.VALIDATING,
            IndexingStage.HASHING,
            IndexingStage.DUPLICATE_CHECK,
            IndexingStage.PARSING,
            IndexingStage.CHUNKING,
            IndexingStage.SAVING_CHUNKS,
            IndexingStage.LOADING_EMBEDDING_MODEL,
            IndexingStage.EMBEDDING,
            IndexingStage.SAVING_VECTORS,
            IndexingStage.FTS_INDEXING,
            IndexingStage.INTEGRITY_VERIFICATION,
            IndexingStage.FINALIZATION,
        )
    }
    assert required <= stages.keys()
    assert all(value >= 0 for value in stages.values())
    assert outcome.diagnostics.failed_stage is None


def test_later_embedding_batch_failure_is_transactional_and_unloads_model(
    tmp_path: Path,
) -> None:
    embedding = FailLaterBatchEmbeddingProvider()
    context = build_application_context(
        _settings(tmp_path),
        embedding_provider=embedding,
        chat_provider=FakeChatProvider(),
    )

    with pytest.raises(EmbeddingGenerationError):
        context.document_workflow.process_and_index(
            original_filename="later-batch.txt",
            data=("A bounded embedding batch must remain transactional. " * 80).encode(),
        )

    documents = context.document_workflow.list_documents()
    assert embedding.batch_sizes == [2]
    assert embedding.loaded is False
    assert len(documents) == 1
    assert documents[0].status is DocumentStatus.FAILED
    assert documents[0].embedded_chunk_count == 0
