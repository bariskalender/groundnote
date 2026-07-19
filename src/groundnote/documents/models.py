"""Provider-neutral document processing models."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field

from groundnote.domain import SupportedFileType


class DuplicateType(StrEnum):
    """Duplicate result categories."""

    NONE = "none"
    EXACT = "exact"


class ParsedSection(BaseModel):
    """One extracted text section from a supported document."""

    text: str = Field(min_length=1, repr=False)
    page_number: int | None = Field(default=None, gt=0)
    section_title: str | None = None
    source_order: int = Field(ge=0)
    warnings: list[str] = Field(default_factory=list)


class ParsedDocument(BaseModel):
    """A parsed document result without local filesystem paths."""

    original_filename: str = Field(min_length=1)
    stored_filename: str = Field(min_length=1)
    file_type: SupportedFileType
    sha256: str = Field(min_length=64, max_length=64)
    file_size_bytes: int = Field(ge=0)
    page_count: int | None = Field(default=None, gt=0)
    sections: list[ParsedSection]
    warnings: list[str] = Field(default_factory=list)


class ValidationResult(BaseModel):
    """Safe validation result for a local file."""

    is_valid: bool
    detected_file_type: SupportedFileType | None = None
    size_bytes: int = Field(ge=0)
    warnings: list[str] = Field(default_factory=list)
    error_code: str | None = None
    user_message: str | None = None


class DuplicateCheckResult(BaseModel):
    """Exact duplicate pre-check result."""

    is_duplicate: bool
    existing_document_id: str | None = None
    sha256: str = Field(min_length=64, max_length=64)
    duplicate_type: DuplicateType = DuplicateType.NONE
    user_message: str
