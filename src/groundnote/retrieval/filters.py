"""Semantic query validation helpers."""

from __future__ import annotations

from groundnote.config import Settings
from groundnote.domain import SupportedFileType
from groundnote.retrieval.errors import EmptyQueryError, RetrievalError
from groundnote.retrieval.models import SemanticQuery


def make_semantic_query(
    text: str,
    *,
    settings: Settings,
    top_k: int | None = None,
    minimum_score: float | None = None,
    document_ids: list[str] | None = None,
    file_types: list[SupportedFileType] | None = None,
    page_numbers: list[int] | None = None,
    metadata_filters: dict[str, str] | None = None,
) -> SemanticQuery:
    """Create a bounded semantic query."""
    cleaned = text.strip()
    if not cleaned:
        raise EmptyQueryError("Query text must not be empty.")
    resolved_top_k = top_k if top_k is not None else settings.top_k
    resolved_minimum = minimum_score if minimum_score is not None else settings.similarity_threshold
    if not 1 <= resolved_top_k <= 20:
        raise RetrievalError("top_k must be between 1 and 20.")
    if resolved_top_k > settings.retrieval_candidate_limit:
        raise RetrievalError("top_k must not exceed retrieval_candidate_limit.")
    if not -1.0 <= resolved_minimum <= 1.0:
        raise RetrievalError("minimum_score must be between -1.0 and 1.0.")
    if page_numbers is not None and any(page <= 0 for page in page_numbers):
        raise RetrievalError("page filters must be positive.")
    return SemanticQuery(
        text=cleaned,
        top_k=resolved_top_k,
        minimum_score=resolved_minimum,
        document_ids=document_ids,
        file_types=file_types,
        page_numbers=page_numbers,
        metadata_filters=metadata_filters,
    )
