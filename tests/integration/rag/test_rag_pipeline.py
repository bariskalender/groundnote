from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

import numpy as np
import pytest

from groundnote.ai.fakes import FakeChatProvider
from groundnote.config import Settings
from groundnote.documents import DuplicateDocumentError
from groundnote.domain import DocumentStatus, SupportedFileType
from groundnote.embeddings import EmbeddingService
from groundnote.rag import RagRequest, RagService
from groundnote.services import DocumentIndexingService, PreEmbeddingIngestionService
from groundnote.storage import (
    MigrationRunner,
    SQLiteConnectionFactory,
    SQLiteDocumentRepository,
    SQLiteUnitOfWorkFactory,
)
from tests.integration.documents.conftest import write_docx, write_text_pdf


class KeywordEmbeddingProvider:
    def __init__(self, *, dimension: int = 1024) -> None:
        self.model_alias = "qwen3-embedding-0.6b"
        self.dimension = dimension
        self.loaded = False

    def load(self) -> None:
        self.loaded = True

    def unload(self) -> None:
        self.loaded = False

    def embed_many(self, texts: Sequence[str], *, batch_size: int = 8) -> object:
        if not self.loaded:
            raise RuntimeError("provider unavailable")
        vectors = np.vstack([self._embed(text) for text in texts]).astype(np.float32)
        return type("Batch", (), {"vectors": vectors})()

    def embed_one(self, text: str) -> np.ndarray:
        if not self.loaded:
            raise RuntimeError("provider unavailable")
        return self._embed(text)

    def _embed(self, text: str) -> np.ndarray:
        lowered = text.lower()
        vector = np.zeros(self.dimension, dtype=np.float32)
        if any(word in lowered for word in ("algebra", "matrix", "vector")):
            vector[0] = 1.0
        elif any(word in lowered for word in ("yerel", "bulut", "belge", "işler")):
            vector[1] = 1.0
        elif any(word in lowered for word in ("pdf", "page", "rag", "retrieval")):
            vector[2] = 1.0
        else:
            vector[3] = 1.0
        return vector


@pytest.fixture
def database_path(tmp_path: Path) -> Path:
    path = tmp_path / "groundnote.sqlite3"
    with SQLiteConnectionFactory(path).open() as connection:
        MigrationRunner().apply(connection)
    return path


def test_full_fake_provider_pipeline_grounded_duplicate_and_clear(
    tmp_path: Path,
    database_path: Path,
) -> None:
    document_id, settings, provider, source = _ingest_and_index(
        tmp_path,
        database_path,
        filename="study.md",
        content="# Algebra\n\nLinear algebra studies matrix and vector spaces.",
    )
    service = _rag_service(
        settings=settings,
        database_path=database_path,
        provider=provider,
        chat=FakeChatProvider(responses=["Linear algebra studies matrix and vector spaces. [S1]"]),
    )

    answer = service.answer(RagRequest(query="What does algebra study?"))

    assert answer.grounded is True
    assert answer.citations[0].source_filename == "study.md"
    assert answer.citations[0].display_label == "study.md — Algebra"
    assert answer.used_context_count == 1
    with pytest.raises(DuplicateDocumentError):
        _ingest_file(tmp_path, database_path, source, settings=settings)

    indexer = DocumentIndexingService(
        settings=settings,
        unit_of_work_factory=SQLiteUnitOfWorkFactory(database_path),
        embedding_service=EmbeddingService(settings=settings, provider=provider),
    )
    indexer.clear_embeddings(document_id)
    unanswerable = service.answer(RagRequest(query="What does algebra study?"))

    assert unanswerable.insufficient_evidence is True
    assert unanswerable.grounded is False
    assert unanswerable.citations == []


def test_markdown_turkish_answer_and_filters(tmp_path: Path, database_path: Path) -> None:
    document_id, settings, provider, _ = _ingest_and_index(
        tmp_path,
        database_path,
        filename="yerel.md",
        content="# Gizlilik\n\nGroundNote belgeleri yerel olarak işler ve bulut API kullanmaz.",
    )
    chat = FakeChatProvider(responses=["GroundNote belgeleri yerel olarak işler. [S1]"])
    service = _rag_service(
        settings=settings,
        database_path=database_path,
        provider=provider,
        chat=chat,
    )

    answer = service.answer(
        RagRequest(
            query="GroundNote belgeleri nerede işler?",
            document_ids=[document_id],
            file_types=[SupportedFileType.MARKDOWN],
        )
    )

    assert answer.response_language == "tr"
    assert answer.grounded is True
    assert answer.citations[0].display_label == "yerel.md — Gizlilik"


def test_pdf_page_and_docx_section_citations(tmp_path: Path, database_path: Path) -> None:
    pdf_dir = tmp_path / "docs-pdf"
    docx_dir = tmp_path / "docs-docx"
    pdf_dir.mkdir()
    docx_dir.mkdir()
    pdf_id, settings, provider, _ = _ingest_and_index(
        tmp_path,
        database_path,
        filename="lecture.pdf",
        path=write_text_pdf(pdf_dir / "lecture.pdf", ["PDF page evidence."]),
    )
    docx_id, _, _, _ = _ingest_and_index(
        tmp_path,
        database_path,
        filename="lecture.docx",
        path=write_docx(docx_dir / "lecture.docx"),
        settings=settings,
        provider=provider,
    )
    service = _rag_service(
        settings=settings,
        database_path=database_path,
        provider=provider,
        chat=FakeChatProvider(
            responses=[
                "The PDF contains page evidence. [S1]",
                "The DOCX contains heading material. [S1]",
            ]
        ),
    )

    pdf_answer = service.answer(RagRequest(query="What does the PDF say?", document_ids=[pdf_id]))
    docx_answer = service.answer(RagRequest(query="RAG retrieval", document_ids=[docx_id]))

    assert "page 1" in pdf_answer.citations[0].display_label
    assert docx_answer.citations[0].source_file_type == SupportedFileType.DOCX
    assert docx_answer.citations[0].section_title is not None


def test_unrelated_query_returns_insufficient_evidence(
    tmp_path: Path,
    database_path: Path,
) -> None:
    _, settings, provider, _ = _ingest_and_index(
        tmp_path,
        database_path,
        filename="study.txt",
        content="Linear algebra studies matrix and vector spaces.",
    )
    service = _rag_service(
        settings=settings,
        database_path=database_path,
        provider=provider,
        chat=FakeChatProvider(),
    )

    answer = service.answer(RagRequest(query="fresh tomato soup", minimum_score=0.2))

    assert answer.insufficient_evidence is True


def _rag_service(
    *,
    settings: Settings,
    database_path: Path,
    provider: KeywordEmbeddingProvider,
    chat: FakeChatProvider,
) -> RagService:
    from groundnote.retrieval import SemanticRetrievalService

    return RagService(
        settings=settings,
        retrieval_service=SemanticRetrievalService(
            settings=settings,
            connection_factory=SQLiteConnectionFactory(database_path),
            embedding_service=EmbeddingService(settings=settings, provider=provider),
        ),
        chat_provider=chat,
    )


def _ingest_and_index(
    tmp_path: Path,
    database_path: Path,
    *,
    filename: str,
    content: str | None = None,
    path: Path | None = None,
    settings: Settings | None = None,
    provider: KeywordEmbeddingProvider | None = None,
) -> tuple[str, Settings, KeywordEmbeddingProvider, Path]:
    document_dir = tmp_path / f"docs-{filename}"
    document_dir.mkdir(parents=True, exist_ok=True)
    source = path or document_dir / filename
    if content is not None:
        source.write_text(content, encoding="utf-8")
    settings = settings or Settings(data_directory=tmp_path / "app")
    provider = provider or KeywordEmbeddingProvider()
    plan = _ingest_file(tmp_path, database_path, source, settings=settings)
    with SQLiteConnectionFactory(database_path).open() as connection:
        document = SQLiteDocumentRepository(connection).get_by_sha256(plan.sha256)
        assert document is not None
        document_id = document.id
    indexer = DocumentIndexingService(
        settings=settings,
        unit_of_work_factory=SQLiteUnitOfWorkFactory(database_path),
        embedding_service=EmbeddingService(settings=settings, provider=provider),
    )
    indexer.index_document(document_id)
    with SQLiteConnectionFactory(database_path).open() as connection:
        document = SQLiteDocumentRepository(connection).get_by_id(document_id)
        assert document.status == DocumentStatus.INDEXED
    return document_id, settings, provider, source


def _ingest_file(
    tmp_path: Path,
    database_path: Path,
    source: Path,
    *,
    settings: Settings,
) -> object:
    ingestion = PreEmbeddingIngestionService(
        settings=settings,
        unit_of_work_factory=SQLiteUnitOfWorkFactory(database_path),
    )
    return ingestion.ingest_file(
        source,
        original_filename=source.name,
        allowed_directory=source.parent,
    )
