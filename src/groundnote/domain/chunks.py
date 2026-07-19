"""Document chunk domain models."""

from __future__ import annotations

from datetime import UTC, datetime

from pydantic import BaseModel, Field, field_validator


class DocumentChunk(BaseModel):
    """Text chunk metadata without embedding arrays in the general model."""

    id: str = Field(min_length=1)
    document_id: str = Field(min_length=1)
    chunk_index: int = Field(ge=0)
    content: str = Field(repr=False)
    page_number: int | None = Field(default=None, gt=0)
    section_title: str | None = None
    character_count: int = Field(ge=0)
    token_estimate: int | None = Field(default=None, ge=0)
    embedding_dimension: int | None = Field(default=None, gt=0)
    embedding_model: str | None = None
    embedding_version: str | None = None
    embedding_dtype: str | None = None
    embedded_at: datetime | None = None
    source_start_order: int | None = Field(default=None, ge=0)
    source_end_order: int | None = Field(default=None, ge=0)
    chunking_version: str | None = None
    metadata_json: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    @field_validator("created_at")
    @classmethod
    def created_at_must_be_timezone_aware(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("created_at must be timezone-aware.")
        return value.astimezone(UTC)

    @field_validator("character_count")
    @classmethod
    def character_count_should_match_content_when_possible(cls, value: int) -> int:
        return value
