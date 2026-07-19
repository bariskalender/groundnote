"""Semantic retrieval service."""

from __future__ import annotations

import json
import time

import numpy as np

from groundnote.config import Settings
from groundnote.domain import SupportedFileType
from groundnote.embeddings import EmbeddingService
from groundnote.retrieval.errors import RetrievalError
from groundnote.retrieval.filters import make_semantic_query
from groundnote.retrieval.models import RetrievalResponse, RetrievalResult, SemanticQuery
from groundnote.retrieval.similarity import cosine_similarity_scores
from groundnote.storage import (
    SearchableChunkEmbedding,
    SQLiteConnectionFactory,
    SQLiteVectorRepository,
)
from groundnote.storage.exceptions import InvalidEmbeddingError as StorageInvalidEmbeddingError
from groundnote.utils import get_logger, sanitize_log_fields


class SemanticRetrievalService:
    """Retrieve ranked chunks using local embeddings and NumPy similarity."""

    def __init__(
        self,
        *,
        settings: Settings,
        connection_factory: SQLiteConnectionFactory,
        embedding_service: EmbeddingService,
    ) -> None:
        self.settings = settings
        self.connection_factory = connection_factory
        self.embedding_service = embedding_service
        self.logger = get_logger(__name__)

    def search(
        self,
        text: str,
        *,
        top_k: int | None = None,
        minimum_score: float | None = None,
        document_ids: list[str] | None = None,
        file_types: list[SupportedFileType] | None = None,
        page_numbers: list[int] | None = None,
    ) -> RetrievalResponse:
        """Return ranked chunks; never generate a natural-language answer."""
        query = make_semantic_query(
            text,
            settings=self.settings,
            top_k=top_k,
            minimum_score=minimum_score,
            document_ids=document_ids,
            file_types=file_types,
            page_numbers=page_numbers,
        )
        return self.search_query(query)

    def search_query(self, query: SemanticQuery) -> RetrievalResponse:
        """Search with a prevalidated query."""
        started = time.perf_counter()
        self.embedding_service.load()
        try:
            query_vector = self.embedding_service.embed_query(query.text)
        finally:
            self.embedding_service.unload()
        with self.connection_factory.open() as connection:
            repository = SQLiteVectorRepository(connection)
            try:
                candidates = repository.list_searchable_embeddings(
                    embedding_model=query_vector.model,
                    embedding_version=query_vector.version,
                    document_ids=query.document_ids,
                    file_types=query.file_types,
                    page_numbers=query.page_numbers,
                    limit=self.settings.retrieval_candidate_limit,
                )
            except StorageInvalidEmbeddingError as exc:
                raise RetrievalError("A stored embedding could not be decoded safely.") from exc
        if not candidates:
            return RetrievalResponse(
                query=query,
                results=[],
                candidate_count=0,
                returned_count=0,
                embedding_model=query_vector.model,
                duration_ms=round((time.perf_counter() - started) * 1000, 3),
                warnings=["no_compatible_indexed_vectors"],
            )
        matrix = np.vstack([candidate.embedding for candidate in candidates]).astype(np.float32)
        scores = cosine_similarity_scores(query_vector.values, matrix, normalized=True)
        ranked = sorted(
            zip(candidates, scores, strict=True),
            key=lambda item: (
                -float(item[1]),
                item[0].chunk.document_id,
                item[0].chunk.chunk_index,
                item[0].chunk.id,
            ),
        )
        results = [
            _to_result(candidate, float(score))
            for candidate, score in ranked
            if float(score) >= query.minimum_score
        ][: query.top_k]
        duration_ms = round((time.perf_counter() - started) * 1000, 3)
        self.logger.info(
            "semantic_retrieval_completed",
            **sanitize_log_fields(
                {
                    "query_character_count": len(query.text),
                    "candidate_count": len(candidates),
                    "returned_count": len(results),
                    "top_k": query.top_k,
                    "minimum_score": query.minimum_score,
                    "embedding_model": query_vector.model,
                    "duration_ms": duration_ms,
                }
            ),
        )
        return RetrievalResponse(
            query=query,
            results=results,
            candidate_count=len(candidates),
            returned_count=len(results),
            embedding_model=query_vector.model,
            duration_ms=duration_ms,
            warnings=[],
        )


def _to_result(candidate: SearchableChunkEmbedding, score: float) -> RetrievalResult:
    chunk = candidate.chunk
    metadata = _metadata_from_json(chunk.metadata_json)
    return RetrievalResult(
        document_id=chunk.document_id,
        chunk_id=chunk.id,
        chunk_index=chunk.chunk_index,
        content=chunk.content,
        score=score,
        page_number=chunk.page_number,
        section_title=chunk.section_title,
        source_filename=candidate.original_filename,
        source_file_type=candidate.file_type,
        source_start_order=chunk.source_start_order,
        source_end_order=chunk.source_end_order,
        metadata=metadata,
    )


def _metadata_from_json(value: str | None) -> dict[str, object]:
    if value is None:
        return {}
    try:
        decoded = json.loads(value)
    except json.JSONDecodeError:
        return {"metadata_warning": "metadata_json_decode_failed"}
    if isinstance(decoded, dict):
        return decoded
    return {"metadata_warning": "metadata_json_not_object"}
