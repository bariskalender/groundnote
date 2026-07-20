from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path

import numpy as np

from groundnote.config import Settings
from groundnote.domain import Document, DocumentChunk, DocumentStatus, SupportedFileType
from groundnote.embeddings import EmbeddingService
from groundnote.retrieval import SemanticRetrievalService
from groundnote.storage import (
    MigrationRunner,
    SerializedEmbedding,
    SQLiteConnectionFactory,
    SQLiteDocumentRepository,
    SQLiteVectorRepository,
    serialize_embedding,
)


class PhaseEmbeddingProvider:
    model_alias = "qwen3-embedding-0.6b"
    dimension = 4

    def __init__(self) -> None:
        self.loaded = False
        self.load_count = 0
        self.unload_count = 0

    def load(self) -> None:
        self.loaded = True
        self.load_count += 1

    def unload(self) -> None:
        self.loaded = False
        self.unload_count += 1

    def embed_one(self, text: str) -> np.ndarray:
        return self._embed(text)

    def embed_many(self, texts: Sequence[str], *, batch_size: int = 8) -> object:
        return type("Batch", (), {"vectors": np.vstack([self._embed(text) for text in texts])})()

    def _embed(self, text: str) -> np.ndarray:
        lowered = text.casefold()
        vector = np.zeros(4, dtype=np.float32)
        if "phase 4" in lowered or "pehase 4" in lowered:
            vector[0] = 1.0
        elif "unique third" in lowered:
            vector[1] = 1.0
        elif "unique second" in lowered:
            vector[2] = 1.0
        else:
            vector[3] = 1.0
        return vector


def test_long_document_chunks_are_ranked_before_final_limit(tmp_path: Path) -> None:
    database_path = _database(tmp_path)
    settings = Settings(
        data_directory=tmp_path / "app",
        embedding_dimension=4,
        retrieval_candidate_limit=50,
        top_k=3,
        rag_retrieval_top_k=3,
        rag_max_chunk_count=3,
        similarity_threshold=-1.0,
    )
    _seed_document(database_path, settings, "doc-1", "phases.docx", phase_chunk_index=120)
    provider = PhaseEmbeddingProvider()
    service = SemanticRetrievalService(
        settings=settings,
        connection_factory=SQLiteConnectionFactory(database_path),
        embedding_service=EmbeddingService(settings=settings, provider=provider),
    )

    response = service.search("What is Phase 4?", minimum_score=-1.0)

    assert response.candidate_count > 120
    assert response.results[0].chunk_index == 120
    assert "Phase 4" in response.results[0].content


def test_later_documents_remain_searchable_and_typo_expansion_works(tmp_path: Path) -> None:
    database_path = _database(tmp_path)
    settings = Settings(
        data_directory=tmp_path / "app",
        embedding_dimension=4,
        retrieval_candidate_limit=50,
        top_k=5,
        rag_retrieval_top_k=5,
        rag_max_chunk_count=5,
        similarity_threshold=-1.0,
    )
    _seed_document(database_path, settings, "doc-1", "first.docx", filler_count=70)
    _seed_document(
        database_path,
        settings,
        "doc-2",
        "second.md",
        filler_count=5,
        unique_text="A unique second document fact names Laurel Index.",
    )
    _seed_document(
        database_path,
        settings,
        "doc-3",
        "third.md",
        filler_count=5,
        phase_chunk_index=3,
        unique_text="A unique third document fact names Cedar Vector.",
    )
    provider = PhaseEmbeddingProvider()
    service = SemanticRetrievalService(
        settings=settings,
        connection_factory=SQLiteConnectionFactory(database_path),
        embedding_service=EmbeddingService(settings=settings, provider=provider),
    )

    second = service.search("unique second Laurel", minimum_score=-1.0)
    typo = service.search("What is pehase 4?", minimum_score=-1.0)

    assert second.results[0].document_id == "doc-2"
    assert typo.results[0].document_id == "doc-3"
    assert "retrieval_query_expanded" in typo.warnings
    assert provider.unload_count == 0


def _database(tmp_path: Path) -> Path:
    database_path = tmp_path / "groundnote.sqlite3"
    with SQLiteConnectionFactory(database_path).open() as connection:
        MigrationRunner().apply(connection)
    return database_path


def _seed_document(
    database_path: Path,
    settings: Settings,
    document_id: str,
    filename: str,
    *,
    filler_count: int = 130,
    phase_chunk_index: int | None = None,
    unique_text: str | None = None,
) -> None:
    now = datetime.now(UTC)
    document = Document(
        id=document_id,
        original_filename=filename,
        stored_filename=f"{document_id}-{filename}",
        file_type=SupportedFileType.DOCX
        if filename.endswith(".docx")
        else SupportedFileType.MARKDOWN,
        sha256=(document_id.encode().hex() * 64)[:64],
        file_size_bytes=1024,
        status=DocumentStatus.INDEXED,
        created_at=now,
        updated_at=now,
        indexed_at=now,
        embedding_model=settings.embedding_model,
        embedding_dimension=settings.embedding_dimension,
        embedding_version=settings.embedding_version,
        chunking_version=settings.chunking_version,
    )
    chunks: list[tuple[DocumentChunk, SerializedEmbedding]] = []
    for index in range(filler_count):
        content = f"Filler chunk {index} about unrelated study notes."
        section = f"Phase {index % 3 + 1}"
        if phase_chunk_index is not None and index == phase_chunk_index:
            content = (
                "Phase 4 - Hybrid Recursive Chunking and Pre-Embedding Ingestion "
                "prepares document chunks before embeddings."
            )
            section = "Phase 4 - Hybrid Recursive Chunking and Pre-Embedding Ingestion"
        if unique_text is not None and index == 2:
            content = unique_text
            section = "Unique Facts"
        chunk = DocumentChunk(
            id=f"{document_id}-chunk-{index}",
            document_id=document_id,
            chunk_index=index,
            content=content,
            page_number=None,
            section_title=section,
            character_count=len(content),
            token_estimate=20,
            embedding_dimension=settings.embedding_dimension,
            embedding_model=settings.embedding_model,
            embedding_version=settings.embedding_version,
            embedding_dtype=settings.embedding_dtype,
            embedded_at=now,
            source_start_order=index,
            source_end_order=index,
            chunking_version=settings.chunking_version,
            created_at=now,
        )
        vector = PhaseEmbeddingProvider()._embed(content)
        data, dimension, dtype = serialize_embedding(vector)
        chunks.append((chunk, SerializedEmbedding(data=data, dimension=dimension, dtype=dtype)))
    with SQLiteConnectionFactory(database_path).open() as connection:
        documents = SQLiteDocumentRepository(connection)
        vectors = SQLiteVectorRepository(connection)
        documents.add(document)
        vectors.add_chunks(chunks)
        connection.commit()
