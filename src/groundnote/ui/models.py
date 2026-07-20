"""Safe, display-oriented models for the Streamlit interface."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum

from groundnote.domain import DocumentStatus, SupportedFileType
from groundnote.rag import Citation, RagAnswer


class UploadOutcomeKind(StrEnum):
    """Possible completed upload workflow outcomes."""

    SUCCESS = "success"
    DUPLICATE = "duplicate"


class UploadStage(StrEnum):
    """Truthful synchronous upload stages exposed to the UI."""

    SAVING = "Saving the upload locally"
    PROCESSING = "Validating, parsing, and creating chunks"
    INDEXING = "Generating local embeddings"
    FINALIZING = "Finalizing the local index"
    READY = "Ready"


@dataclass(frozen=True)
class DocumentSummary:
    """Privacy-safe document information for status and filters."""

    document_id: str
    original_filename: str
    file_type: SupportedFileType
    status: DocumentStatus
    file_size_bytes: int
    page_count: int | None
    chunk_count: int
    embedded_chunk_count: int
    created_at: datetime
    indexed_at: datetime | None
    embedding_model: str | None
    error_message: str | None = None


@dataclass(frozen=True)
class UploadOutcome:
    """Completed upload result without bytes, hashes, paths, or vectors."""

    kind: UploadOutcomeKind
    document: DocumentSummary
    section_count: int | None
    warnings: list[str] = field(default_factory=list)
    duration_ms: float = 0.0


@dataclass(frozen=True)
class CitationView:
    """Trusted citation fields prepared for rendering."""

    citation_id: str
    label: str
    file_type: str
    page_number: int | None
    section_title: str | None
    chunk_number: int
    score: float | None


@dataclass(frozen=True)
class QuestionOutcome:
    """Latest single-turn answer and its active safe filters."""

    question: str
    answer: RagAnswer
    document_ids: tuple[str, ...]
    file_types: tuple[SupportedFileType, ...]


@dataclass(frozen=True)
class ChatMessageState:
    """Session-only chat message safe for Streamlit state."""

    message_id: str
    role: str
    text: str
    citations: tuple[Citation, ...] = ()
    status: str = "complete"
    duration_ms: float | None = None
    warnings: tuple[str, ...] = ()
