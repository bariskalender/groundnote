"""Document validation and parsing package."""

from groundnote.documents.errors import (
    ChunkCountLimitError,
    CorruptDocumentError,
    DocumentError,
    DocxArchiveSafetyError,
    DuplicateDocumentError,
    EmptyDocumentError,
    EncodingError,
    EncryptedDocumentError,
    ExtractedTextLimitError,
    FileTooLargeError,
    NoExtractableTextError,
    ParserNotFoundError,
    PdfPageLimitError,
    UnsafeFileError,
    UnsupportedFileTypeError,
)
from groundnote.documents.hashing import calculate_sha256
from groundnote.documents.managed_files import (
    ManagedFileCleanupResult,
    ManagedFileCleanupStatus,
    remove_managed_document_copy,
)
from groundnote.documents.models import (
    DuplicateCheckResult,
    DuplicateType,
    ParsedDocument,
    ParsedSection,
    ValidationResult,
)
from groundnote.documents.normalization import normalize_text
from groundnote.documents.registry import ParserRegistry, default_parser_registry
from groundnote.documents.service import DocumentProcessingService
from groundnote.documents.validation import (
    detect_file_type,
    generate_safe_stored_filename,
    safe_display_filename,
    validate_local_file,
)

__all__ = [
    "CorruptDocumentError",
    "ChunkCountLimitError",
    "DocumentError",
    "DocumentProcessingService",
    "DuplicateDocumentError",
    "DuplicateCheckResult",
    "DuplicateType",
    "DocxArchiveSafetyError",
    "EmptyDocumentError",
    "EncodingError",
    "EncryptedDocumentError",
    "ExtractedTextLimitError",
    "FileTooLargeError",
    "ManagedFileCleanupResult",
    "ManagedFileCleanupStatus",
    "NoExtractableTextError",
    "PdfPageLimitError",
    "ParsedDocument",
    "ParsedSection",
    "ParserNotFoundError",
    "ParserRegistry",
    "UnsafeFileError",
    "UnsupportedFileTypeError",
    "ValidationResult",
    "calculate_sha256",
    "default_parser_registry",
    "detect_file_type",
    "generate_safe_stored_filename",
    "normalize_text",
    "remove_managed_document_copy",
    "safe_display_filename",
    "validate_local_file",
]
