"""Document processing service for Phase 3 validation and parsing."""

from __future__ import annotations

import time
from contextlib import nullcontext
from pathlib import Path
from re import fullmatch
from typing import Protocol

from groundnote.config import Settings
from groundnote.documents.errors import (
    DocumentError,
    DuplicateDocumentError,
    EmptyDocumentError,
    ExtractedTextLimitError,
    FileTooLargeError,
    UnsafeFileError,
    UnsupportedFileTypeError,
)
from groundnote.documents.hashing import calculate_sha256
from groundnote.documents.models import DuplicateCheckResult, DuplicateType, ParsedDocument
from groundnote.documents.registry import ParserRegistry, default_parser_registry
from groundnote.documents.validation import (
    generate_safe_stored_filename,
    safe_display_filename,
    validate_local_file,
)
from groundnote.domain import Document
from groundnote.performance import IndexingMetricsCollector, IndexingStage
from groundnote.storage import DocumentRepository
from groundnote.utils import get_logger, safe_log_info, sanitize_log_fields


class DuplicateLookup(Protocol):
    """Minimal duplicate lookup contract."""

    def get_by_sha256(self, sha256: str) -> Document | None: ...


class DocumentProcessingService:
    """Coordinate validation, hashing, duplicate pre-checking, and parsing."""

    def __init__(
        self,
        *,
        settings: Settings,
        duplicate_lookup: DuplicateLookup | None = None,
        registry: ParserRegistry | None = None,
    ) -> None:
        self.settings = settings
        self.duplicate_lookup = duplicate_lookup
        self.registry = registry or default_parser_registry(settings)
        self.logger = get_logger(__name__)

    def check_duplicate(self, sha256: str) -> DuplicateCheckResult:
        if self.duplicate_lookup is None:
            return DuplicateCheckResult(
                is_duplicate=False,
                sha256=sha256,
                duplicate_type=DuplicateType.NONE,
                user_message="No exact duplicate was found.",
            )
        existing = self.duplicate_lookup.get_by_sha256(sha256)
        if existing is None:
            return DuplicateCheckResult(
                is_duplicate=False,
                sha256=sha256,
                duplicate_type=DuplicateType.NONE,
                user_message="No exact duplicate was found.",
            )
        return DuplicateCheckResult(
            is_duplicate=True,
            existing_document_id=existing.id,
            sha256=sha256,
            duplicate_type=DuplicateType.EXACT,
            user_message="This file is an exact duplicate of an existing document.",
        )

    def process_file(
        self,
        file_path: Path,
        *,
        original_filename: str,
        allowed_directory: Path,
        stored_filename: str | None = None,
        precomputed_sha256: str | None = None,
        metrics: IndexingMetricsCollector | None = None,
    ) -> ParsedDocument:
        started = time.perf_counter()
        safe_name = safe_display_filename(original_filename)
        with metrics.measure(IndexingStage.VALIDATING) if metrics else nullcontext():
            validation = validate_local_file(
                file_path,
                original_filename=safe_name,
                allowed_directory=allowed_directory,
                settings=self.settings,
            )
        if not validation.is_valid or validation.detected_file_type is None:
            raise _validation_error(validation.error_code, validation.user_message)
        if metrics is not None:
            metrics.file_size_bytes = validation.size_bytes
        if precomputed_sha256 is None:
            with metrics.measure(IndexingStage.HASHING) if metrics else nullcontext():
                sha256 = calculate_sha256(file_path)
        else:
            sha256 = _validated_sha256(precomputed_sha256)
            if metrics is not None:
                metrics.hash_reused = True
                metrics.record_zero(IndexingStage.HASHING)
        with metrics.measure(IndexingStage.DUPLICATE_CHECK) if metrics else nullcontext():
            duplicate = self.check_duplicate(sha256)
        if duplicate.is_duplicate:
            self._log_result(
                "document_duplicate_detected",
                safe_name=safe_name,
                file_type=validation.detected_file_type.value,
                file_size_bytes=validation.size_bytes,
                warning_count=len(validation.warnings),
                duration_ms=_elapsed_ms(started),
            )
            raise DuplicateDocumentError(
                duplicate.user_message,
                existing_document_id=duplicate.existing_document_id,
            )
        resolved_stored_filename = (
            _validate_stored_filename(stored_filename)
            if stored_filename is not None
            else generate_safe_stored_filename(safe_name)
        )
        parser = self.registry.get(validation.detected_file_type)
        try:
            with metrics.measure(IndexingStage.PARSING) if metrics else nullcontext():
                parsed = parser.parse(
                    file_path,
                    original_filename=safe_name,
                    stored_filename=resolved_stored_filename,
                    sha256=sha256,
                    file_size_bytes=validation.size_bytes,
                )
        except DocumentError as exc:
            self._log_result(
                "document_parse_failed",
                safe_name=safe_name,
                file_type=validation.detected_file_type.value,
                parser_name=parser.__class__.__name__,
                file_size_bytes=validation.size_bytes,
                error_code=exc.error_code,
                duration_ms=_elapsed_ms(started),
            )
            raise
        extracted_character_count = sum(len(section.text) for section in parsed.sections)
        if extracted_character_count > self.settings.maximum_extracted_characters:
            raise ExtractedTextLimitError()
        if metrics is not None:
            metrics.extracted_character_count = extracted_character_count
            metrics.page_count = parsed.page_count
        self._log_result(
            "document_parsed",
            safe_name=safe_name,
            file_type=parsed.file_type.value,
            parser_name=parser.__class__.__name__,
            file_size_bytes=parsed.file_size_bytes,
            section_count=len(parsed.sections),
            page_count=parsed.page_count,
            warning_count=len(parsed.warnings),
            duration_ms=_elapsed_ms(started),
        )
        return parsed

    def _log_result(self, event: str, **fields: object) -> None:
        safe_log_info(self.logger, event, **sanitize_log_fields(dict(fields)))


def make_document_processing_service(
    *,
    settings: Settings,
    duplicate_lookup: DocumentRepository | None = None,
) -> DocumentProcessingService:
    """Factory for the default document processing service."""
    return DocumentProcessingService(settings=settings, duplicate_lookup=duplicate_lookup)


def _elapsed_ms(started: float) -> float:
    return round((time.perf_counter() - started) * 1000, 3)


def _validation_error(error_code: str | None, message: str | None) -> DocumentError:
    error_types: dict[str, type[DocumentError]] = {
        UnsupportedFileTypeError.error_code: UnsupportedFileTypeError,
        FileTooLargeError.error_code: FileTooLargeError,
        EmptyDocumentError.error_code: EmptyDocumentError,
        UnsafeFileError.error_code: UnsafeFileError,
    }
    error_type = error_types.get(error_code or "", DocumentError)
    return error_type(message)


def _validate_stored_filename(filename: str) -> str:
    safe_name = safe_display_filename(filename)
    if safe_name != filename:
        raise UnsafeFileError("The stored filename is not safe.")
    return safe_name


def _validated_sha256(value: str) -> str:
    normalized = value.strip().casefold()
    if fullmatch(r"[0-9a-f]{64}", normalized) is None:
        raise UnsafeFileError("The precomputed document hash is invalid.")
    return normalized
