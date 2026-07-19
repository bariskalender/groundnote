"""Semantic retrieval models."""

from __future__ import annotations

from dataclasses import dataclass, field

from groundnote.domain import SupportedFileType


@dataclass(frozen=True)
class SemanticQuery:
    """Validated semantic search request."""

    text: str
    top_k: int
    minimum_score: float
    document_ids: list[str] | None = None
    file_types: list[SupportedFileType] | None = None
    page_numbers: list[int] | None = None
    metadata_filters: dict[str, str] | None = None


@dataclass(frozen=True)
class RetrievalResult:
    """Ranked chunk result with citation metadata."""

    document_id: str
    chunk_id: str
    chunk_index: int
    content: str
    score: float
    page_number: int | None
    section_title: str | None
    source_filename: str
    source_file_type: SupportedFileType
    source_start_order: int | None
    source_end_order: int | None
    metadata: dict[str, object] = field(default_factory=dict)


@dataclass(frozen=True)
class RetrievalResponse:
    """Semantic retrieval response without generated answers."""

    query: SemanticQuery
    results: list[RetrievalResult]
    candidate_count: int
    returned_count: int
    embedding_model: str
    duration_ms: float
    warnings: list[str] = field(default_factory=list)
