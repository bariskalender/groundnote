"""Semantic retrieval service."""

from __future__ import annotations

import json
import re
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
    LexicalChunkMatch,
    SearchableChunkEmbedding,
    SQLiteConnectionFactory,
    SQLiteVectorRepository,
)
from groundnote.storage.exceptions import InvalidEmbeddingError as StorageInvalidEmbeddingError
from groundnote.utils import get_logger, safe_log_info, safe_log_warning, sanitize_log_fields


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
        embedding_started = time.perf_counter()
        try:
            self.embedding_service.load()
            query_vector = self.embedding_service.embed_query(query.text)
        except BaseException:
            self._unload_embedding_model()
            raise
        finally:
            if not self.settings.keep_models_loaded:
                self._unload_embedding_model()
        embedding_ms = _elapsed_ms(embedding_started)
        lexical_started = time.perf_counter()
        fts_query, expanded_query, expansion_warning = self._expand_lexical_query(query)
        with self.connection_factory.open() as connection:
            repository = SQLiteVectorRepository(connection)
            try:
                candidates = repository.list_searchable_embeddings(
                    embedding_model=query_vector.model,
                    embedding_version=query_vector.version,
                    document_ids=query.document_ids,
                    file_types=query.file_types,
                    page_numbers=query.page_numbers,
                    limit=None,
                )
                lexical_matches = repository.search_lexical_chunks(
                    query=fts_query,
                    embedding_model=query_vector.model,
                    embedding_version=query_vector.version,
                    document_ids=query.document_ids,
                    file_types=query.file_types,
                    page_numbers=query.page_numbers,
                    limit=max(self.settings.retrieval_candidate_limit, query.top_k * 4),
                )
            except StorageInvalidEmbeddingError as exc:
                raise RetrievalError("A stored embedding could not be decoded safely.") from exc
        lexical_ms = _elapsed_ms(lexical_started)
        if not candidates:
            return RetrievalResponse(
                query=query,
                results=[],
                candidate_count=0,
                returned_count=0,
                embedding_model=query_vector.model,
                duration_ms=round((time.perf_counter() - started) * 1000, 3),
                warnings=["no_compatible_indexed_vectors"],
                stage_timings_ms={
                    "query_embedding": embedding_ms,
                    "lexical_search": lexical_ms,
                },
            )
        vector_started = time.perf_counter()
        matrix = np.vstack([candidate.embedding for candidate in candidates]).astype(np.float32)
        scores = cosine_similarity_scores(query_vector.values, matrix, normalized=True)
        vector_ms = _elapsed_ms(vector_started)
        rank_started = time.perf_counter()
        ranked = self._rank_hybrid(
            query=query,
            candidates=candidates,
            scores=[float(score) for score in scores],
            lexical_matches=lexical_matches,
            expanded_query=expanded_query,
        )
        ranked = [
            (candidate, combined_score, mode, semantic_score)
            for candidate, combined_score, mode, semantic_score in ranked
            if semantic_score >= query.minimum_score or mode == "hybrid"
        ][: self.settings.retrieval_candidate_limit]
        results = [
            _to_result(candidate, semantic_score, retrieval_mode=mode)
            for candidate, _combined_score, mode, semantic_score in ranked[: query.top_k]
        ]
        results = self._include_adjacent_context(results, candidates, limit=query.top_k)
        rank_ms = _elapsed_ms(rank_started)
        duration_ms = round((time.perf_counter() - started) * 1000, 3)
        warnings = []
        if expansion_warning is not None:
            warnings.append(expansion_warning)
        if lexical_matches:
            warnings.append("hybrid_retrieval_used")
        safe_log_info(
            self.logger,
            "semantic_retrieval_completed",
            **sanitize_log_fields(
                {
                    "query_character_count": len(query.text),
                    "candidate_count": len(candidates),
                    "lexical_candidate_count": len(lexical_matches),
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
            warnings=warnings,
            stage_timings_ms={
                "query_embedding": embedding_ms,
                "lexical_search": lexical_ms,
                "vector_scoring": vector_ms,
                "hybrid_ranking": rank_ms,
            },
        )

    def _unload_embedding_model(self) -> None:
        try:
            self.embedding_service.unload()
        except Exception:
            safe_log_warning(
                self.logger,
                "embedding_model_unload_failed",
                embedding_model=self.settings.embedding_model,
            )

    def release_for_chat(self) -> None:
        """Release GroundNote's query embedding provider before chat model activation."""
        self._unload_embedding_model()

    def _expand_lexical_query(self, query: SemanticQuery) -> tuple[str, str, str | None]:
        tokens = _query_tokens(query.text)
        expanded = list(tokens)
        warning: str | None = None
        with self.connection_factory.open() as connection:
            vocabulary = SQLiteVectorRepository(connection).vocabulary_terms(
                document_ids=query.document_ids,
                file_types=query.file_types,
            )
        vocabulary_set = set(vocabulary)
        for index, token in enumerate(tokens):
            if not _is_typo_candidate(token):
                continue
            corrections = [
                term
                for term in vocabulary_set
                if term != token and _damerau_distance_one(token, term)
            ]
            if len(corrections) == 1:
                expanded[index] = corrections[0]
                warning = "retrieval_query_expanded"
        if not expanded:
            return _fts_escape(query.text), query.text, warning
        fts_query = " OR ".join(_fts_escape(token) for token in dict.fromkeys([*tokens, *expanded]))
        return fts_query, " ".join(expanded), warning

    def _rank_hybrid(
        self,
        *,
        query: SemanticQuery,
        candidates: list[SearchableChunkEmbedding],
        scores: list[float],
        lexical_matches: list[LexicalChunkMatch],
        expanded_query: str,
    ) -> list[tuple[SearchableChunkEmbedding, float, str, float]]:
        score_map = {
            candidate.chunk.id: score for candidate, score in zip(candidates, scores, strict=True)
        }
        semantic_rank = {
            candidate.chunk.id: rank
            for rank, candidate in enumerate(
                sorted(
                    candidates,
                    key=lambda item: (
                        -score_map[item.chunk.id],
                        item.chunk.document_id,
                        item.chunk.chunk_index,
                        item.chunk.id,
                    ),
                ),
                start=1,
            )
        }
        lexical_rank = {match.chunk_id: rank for rank, match in enumerate(lexical_matches, start=1)}
        query_normalized = _normalize_for_match(expanded_query)
        ranked: list[tuple[SearchableChunkEmbedding, float, str, float]] = []
        for candidate in candidates:
            chunk_id = candidate.chunk.id
            semantic = score_map[chunk_id]
            lexical_boost = 0.0
            mode = "semantic"
            if chunk_id in lexical_rank:
                lexical_boost = 1.0 / (60.0 + lexical_rank[chunk_id])
                mode = "hybrid"
            semantic_boost = 1.0 / (60.0 + semantic_rank[chunk_id])
            heading_boost = _heading_boost(query_normalized, candidate)
            combined = semantic + lexical_boost + semantic_boost + heading_boost
            ranked.append((candidate, combined, mode, semantic))
        return sorted(
            ranked,
            key=lambda item: (
                -item[1],
                item[0].chunk.document_id,
                item[0].chunk.chunk_index,
                item[0].chunk.id,
            ),
        )

    def _include_adjacent_context(
        self,
        results: list[RetrievalResult],
        candidates: list[SearchableChunkEmbedding],
        *,
        limit: int,
    ) -> list[RetrievalResult]:
        if len(results) >= limit:
            return results
        candidate_by_position = {
            (candidate.chunk.document_id, candidate.chunk.chunk_index): candidate
            for candidate in candidates
        }
        seen = {result.chunk_id for result in results}
        expanded = list(results)
        for result in results:
            if len(expanded) >= limit:
                break
            adjacent = candidate_by_position.get((result.document_id, result.chunk_index + 1))
            if adjacent is None or adjacent.chunk.id in seen:
                continue
            if adjacent.chunk.page_number != result.page_number:
                continue
            if adjacent.chunk.section_title != result.section_title:
                continue
            adjacent_result = _to_result(
                adjacent,
                max(result.score - 0.0001, -1.0),
                retrieval_mode="adjacent",
            )
            expanded.append(adjacent_result)
            seen.add(adjacent.chunk.id)
        return sorted(
            expanded,
            key=lambda item: (-item.score, item.document_id, item.chunk_index, item.chunk_id),
        )[:limit]


def _to_result(
    candidate: SearchableChunkEmbedding,
    score: float,
    *,
    retrieval_mode: str,
) -> RetrievalResult:
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
        retrieval_mode=retrieval_mode,
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


def _elapsed_ms(started: float) -> float:
    return round((time.perf_counter() - started) * 1000, 3)


def _query_tokens(text: str) -> list[str]:
    return [token.casefold() for token in re.findall(r"[\w.-]+", text, flags=re.UNICODE)]


def _is_typo_candidate(token: str) -> bool:
    if len(token) < 5:
        return False
    if "_" in token or "." in token or "-" in token:
        return False
    return any(character.isalpha() for character in token)


def _damerau_distance_one(left: str, right: str) -> bool:
    if left == right or abs(len(left) - len(right)) > 1:
        return False
    if len(left) == len(right):
        differences = [
            index for index, pair in enumerate(zip(left, right, strict=True)) if pair[0] != pair[1]
        ]
        if len(differences) == 1:
            return True
        if len(differences) == 2:
            first, second = differences
            return (
                first + 1 == second
                and left[first] == right[second]
                and left[second] == right[first]
            )
        return False
    shorter, longer = (left, right) if len(left) < len(right) else (right, left)
    return any(shorter == longer[:index] + longer[index + 1 :] for index in range(len(longer)))


def _fts_escape(token: str) -> str:
    safe = token.replace('"', '""')
    return f'"{safe}"'


def _normalize_for_match(text: str) -> str:
    return " ".join(_query_tokens(text))


def _heading_boost(query_normalized: str, candidate: SearchableChunkEmbedding) -> float:
    heading = _normalize_for_match(candidate.chunk.section_title or "")
    filename = _normalize_for_match(candidate.original_filename)
    query_numbered_terms = set(re.findall(r"\b[\w-]+\s+\d+\b", query_normalized))
    heading_numbered_terms = set(re.findall(r"\b[\w-]+\s+\d+\b", heading))
    if query_numbered_terms & heading_numbered_terms:
        return 0.45
    if heading and heading in query_normalized:
        return 0.35
    if query_normalized and query_normalized in heading:
        return 0.30
    if filename and any(token in filename for token in query_normalized.split()):
        return 0.05
    return 0.0
