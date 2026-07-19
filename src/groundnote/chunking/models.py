"""Provider-neutral chunking models."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, Field, field_validator

from groundnote.documents import DuplicateCheckResult, DuplicateType, ParsedDocument
from groundnote.domain import DocumentStatus, SupportedFileType


class ChunkingSettings(BaseModel):
    """Validated chunking configuration."""

    target_characters: int = 900
    maximum_characters: int = 1400
    overlap_characters: int = 120
    minimum_characters: int = 120
    version: str = "hybrid-recursive-v1"

    @field_validator("target_characters", "maximum_characters", "minimum_characters")
    @classmethod
    def sizes_must_be_positive(cls, value: int) -> int:
        if value <= 0:
            raise ValueError("chunk sizes must be positive.")
        return value

    @field_validator("overlap_characters")
    @classmethod
    def overlap_must_be_non_negative(cls, value: int) -> int:
        if value < 0:
            raise ValueError("overlap must be non-negative.")
        return value

    @field_validator("version")
    @classmethod
    def version_must_be_present(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("chunking version must be present.")
        return value

    def model_post_init(self, __context: object) -> None:
        if self.maximum_characters < self.target_characters:
            raise ValueError("maximum must be greater than or equal to target.")
        if self.overlap_characters >= self.target_characters:
            raise ValueError("overlap must be smaller than target.")
        if self.minimum_characters > self.target_characters:
            raise ValueError("minimum must be less than or equal to target.")


class ChunkCandidate(BaseModel):
    """Intermediate chunking unit derived from parsed sections."""

    text: str = Field(min_length=1, repr=False)
    page_number: int | None = Field(default=None, gt=0)
    section_title: str | None = None
    source_order: int = Field(ge=0)
    source_section_index: int = Field(ge=0)
    warnings: list[str] = Field(default_factory=list)


class TextChunk(BaseModel):
    """Final chunking result before embeddings are generated."""

    document_id: str | None = None
    chunk_index: int = Field(ge=0)
    content: str = Field(min_length=1, repr=False)
    page_number: int | None = Field(default=None, gt=0)
    section_title: str | None = None
    character_count: int = Field(gt=0)
    token_estimate: int | None = Field(default=None, ge=1)
    source_start_order: int = Field(ge=0)
    source_end_order: int = Field(ge=0)
    chunking_version: str = Field(min_length=1)
    metadata: dict[str, Any] = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)


class ChunkingResult(BaseModel):
    """Deterministic chunking output."""

    chunks: list[TextChunk]
    warnings: list[str] = Field(default_factory=list)
    original_section_count: int = Field(ge=0)
    chunk_count: int = Field(ge=0)
    total_character_count: int = Field(ge=0)
    chunking_version: str = Field(min_length=1)


class IngestionPlan(BaseModel):
    """Pre-embedding ingestion result without embeddings."""

    parsed_document: ParsedDocument = Field(repr=False)
    chunks: list[TextChunk] = Field(repr=False)
    sha256: str = Field(min_length=64, max_length=64)
    duplicate_status: DuplicateCheckResult = Field(
        default_factory=lambda: DuplicateCheckResult(
            is_duplicate=False,
            sha256="0" * 64,
            duplicate_type=DuplicateType.NONE,
            user_message="No exact duplicate was found.",
        )
    )
    document_status: DocumentStatus = DocumentStatus.PENDING_EMBEDDING
    embedding_model: str | None = None
    embedding_dimension: int | None = Field(default=None, gt=0)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    warnings: list[str] = Field(default_factory=list)


class ChunkSourceMetadata(BaseModel):
    """Safe metadata attached to each chunk."""

    source_filename: str
    source_file_type: SupportedFileType
    source_start_order: int
    source_end_order: int
    warnings: list[str] = Field(default_factory=list)
