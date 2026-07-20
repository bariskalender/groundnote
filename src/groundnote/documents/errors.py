"""Application-specific document processing errors."""

from __future__ import annotations


class DocumentError(RuntimeError):
    """Base error for safe document validation and parsing failures."""

    error_code = "document_error"
    user_message = "The document could not be processed."

    def __init__(self, user_message: str | None = None) -> None:
        super().__init__(user_message or self.user_message)


class UnsupportedFileTypeError(DocumentError):
    error_code = "unsupported_file_type"
    user_message = "This file type is not supported."


class FileTooLargeError(DocumentError):
    error_code = "file_too_large"
    user_message = "The file is larger than the configured upload limit."


class EmptyDocumentError(DocumentError):
    error_code = "empty_document"
    user_message = "The document is empty."


class CorruptDocumentError(DocumentError):
    error_code = "corrupt_document"
    user_message = "The document appears to be corrupted or unreadable."


class EncryptedDocumentError(DocumentError):
    error_code = "encrypted_document"
    user_message = "Encrypted documents are not supported."


class NoExtractableTextError(DocumentError):
    error_code = "no_extractable_text"
    user_message = "No readable text could be extracted. OCR is not supported in this version."


class UnsafeFileError(DocumentError):
    error_code = "unsafe_file"
    user_message = "The file name or path is not safe to process."


class EncodingError(DocumentError):
    error_code = "encoding_error"
    user_message = "The text file encoding is not supported."


class DuplicateDocumentError(DocumentError):
    error_code = "duplicate_document"
    user_message = "This file is an exact duplicate of an existing document."

    def __init__(
        self,
        user_message: str | None = None,
        *,
        existing_document_id: str | None = None,
    ) -> None:
        super().__init__(user_message)
        self.existing_document_id = existing_document_id


class ParserNotFoundError(DocumentError):
    error_code = "parser_not_found"
    user_message = "No parser is available for this file type."
