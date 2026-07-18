"""Document domain models."""

from __future__ import annotations

import re
from datetime import UTC, datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, field_validator

SHA256_RE = re.compile(r"^[a-fA-F0-9]{64}$")


def _utc_now() -> datetime:
    return datetime.now(UTC)


class SupportedFileType(StrEnum):
    """File types supported by the future MVP parser layer."""

    PDF = "pdf"
    DOCX = "docx"
    TXT = "txt"
    MARKDOWN = "markdown"


class DocumentStatus(StrEnum):
    """Document lifecycle states used by storage and future indexing flows."""

    PENDING = "pending"
    PARSING = "parsing"
    PARSED = "parsed"
    PENDING_EMBEDDING = "pending_embedding"
    INDEXING = "indexing"
    INDEXED = "indexed"
    FAILED = "failed"
    INCOMPATIBLE_INDEX = "incompatible_index"


class Document(BaseModel):
    """A stored document record without exposing local filesystem paths."""

    model_config = ConfigDict(use_enum_values=False)

    id: str = Field(min_length=1)
    original_filename: str = Field(min_length=1)
    stored_filename: str = Field(min_length=1)
    file_type: SupportedFileType
    sha256: str
    file_size_bytes: int = Field(ge=0)
    page_count: int | None = Field(default=None, gt=0)
    status: DocumentStatus = DocumentStatus.PENDING
    created_at: datetime = Field(default_factory=_utc_now)
    updated_at: datetime = Field(default_factory=_utc_now)
    indexed_at: datetime | None = None
    error_message: str | None = None
    embedding_model: str | None = None
    embedding_dimension: int | None = Field(default=None, gt=0)
    chunking_version: str | None = None

    @field_validator("sha256")
    @classmethod
    def sha256_must_be_valid(cls, value: str) -> str:
        if SHA256_RE.fullmatch(value) is None:
            raise ValueError("sha256 must be a 64-character hexadecimal digest.")
        return value.lower()

    @field_validator("created_at", "updated_at", "indexed_at")
    @classmethod
    def timestamps_must_be_timezone_aware(cls, value: datetime | None) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("timestamps must be timezone-aware.")
        return value.astimezone(UTC)

    def __repr__(self) -> str:
        return (
            "Document("
            f"id={self.id!r}, original_filename={self.original_filename!r}, "
            f"file_type={self.file_type.value!r}, status={self.status.value!r})"
        )
