"""Provider-neutral RAG models."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

from groundnote.domain import SupportedFileType

ResponseLanguage = Literal["tr", "en", "auto"]


@dataclass(frozen=True)
class RagRequest:
    """Single-turn grounded answer request."""

    query: str = field(repr=False)
    document_ids: list[str] | None = None
    file_types: list[SupportedFileType] | None = None
    page_numbers: list[int] | None = None
    top_k: int | None = None
    minimum_score: float | None = None
    response_language: ResponseLanguage | None = None
    include_citations: bool = True
    metadata: dict[str, object] = field(default_factory=dict, repr=False)


@dataclass(frozen=True)
class RagContextItem:
    """One retrieved source chunk selected for generation context."""

    citation_id: str
    document_id: str
    chunk_id: str
    chunk_index: int
    content: str = field(repr=False)
    score: float
    source_filename: str
    source_file_type: SupportedFileType
    page_number: int | None
    section_title: str | None
    source_start_order: int | None
    source_end_order: int | None
    metadata: dict[str, object] = field(default_factory=dict, repr=False)


@dataclass(frozen=True)
class Citation:
    """Trusted citation metadata mapped from retrieved context."""

    citation_id: str
    document_id: str
    chunk_id: str
    source_filename: str
    source_file_type: SupportedFileType
    page_number: int | None
    section_title: str | None
    chunk_index: int
    display_label: str
    score: float | None = None


@dataclass(frozen=True)
class RagAnswer:
    """Generated answer with grounding metadata."""

    answer: str = field(repr=False)
    citations: list[Citation]
    grounded: bool
    insufficient_evidence: bool
    response_language: Literal["tr", "en"]
    model: str
    prompt_version: str
    retrieved_count: int
    used_context_count: int
    warnings: list[str]
    duration_ms: float


@dataclass(frozen=True)
class RagResponse:
    """RAG response with a private request summary."""

    request: RagRequest = field(repr=False)
    answer: RagAnswer
    retrieval_candidate_count: int
    retrieval_returned_count: int
    model: str
    warnings: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class PromptBundle:
    """Separated prompt messages for local chat generation."""

    system_prompt: str = field(repr=False)
    user_prompt: str = field(repr=False)
    prompt_version: str
    allowed_citation_ids: list[str]
