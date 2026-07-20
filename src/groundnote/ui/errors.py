"""User-safe exception mapping for the Streamlit boundary."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from groundnote.ai import FoundryCatalogError, FoundryModelUnavailableError, FoundryProviderError
from groundnote.chunking.errors import ChunkingError
from groundnote.documents import (
    CorruptDocumentError,
    DocumentError,
    DuplicateDocumentError,
    EmptyDocumentError,
    EncodingError,
    EncryptedDocumentError,
    FileTooLargeError,
    NoExtractableTextError,
    ParserNotFoundError,
    UnsafeFileError,
    UnsupportedFileTypeError,
)
from groundnote.embeddings import (
    EmbeddingError,
    EmbeddingGenerationError,
    EmbeddingModelLoadError,
    IndexingError,
)
from groundnote.rag import (
    ChatGenerationError,
    ChatModelLoadError,
    CitationValidationError,
    EmptyRagQueryError,
    InvalidChatResponseError,
    RagError,
    RagRetrievalError,
)
from groundnote.storage import MigrationError, StorageError


class MessageSeverity(StrEnum):
    """Supported Streamlit notice severities."""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


@dataclass(frozen=True)
class UiMessage:
    """Display-ready message without internal exception details."""

    title: str
    message: str
    severity: MessageSeverity
    remediation: str | None = None


class UiWorkflowError(RuntimeError):
    """Base class for expected UI orchestration errors."""


class NoFileSelectedError(UiWorkflowError):
    """Raised when upload processing is requested without a file."""


class NoIndexedDocumentsError(UiWorkflowError):
    """Raised when a question has no searchable source."""


class InvalidFilterError(UiWorkflowError):
    """Raised when uncontrolled filter values are invalid."""


class DatabaseBootstrapError(UiWorkflowError):
    """Raised when local settings or storage cannot initialize."""


def map_exception(error: BaseException) -> UiMessage:
    """Map known failures without exposing paths, SQL, prompts, or stack traces."""
    if isinstance(error, NoFileSelectedError):
        return UiMessage(
            "No document selected",
            "Choose a supported document first.",
            MessageSeverity.INFO,
        )
    if isinstance(error, UnsupportedFileTypeError):
        return UiMessage(
            "Unsupported file type",
            "GroundNote supports PDF, DOCX, TXT, and Markdown files.",
            MessageSeverity.WARNING,
        )
    if isinstance(error, FileTooLargeError):
        return UiMessage(
            "File is too large",
            "The document exceeds the configured local upload limit.",
            MessageSeverity.WARNING,
            "Choose a smaller document or adjust the local upload setting.",
        )
    if isinstance(error, EmptyDocumentError):
        return UiMessage(
            "Empty document",
            "The selected document has no content.",
            MessageSeverity.WARNING,
        )
    if isinstance(error, UnsafeFileError):
        return UiMessage(
            "Unsafe filename",
            "The selected filename cannot be processed safely.",
            MessageSeverity.WARNING,
            "Rename the file and try again.",
        )
    if isinstance(error, EncryptedDocumentError):
        return UiMessage(
            "Encrypted PDF",
            "Encrypted PDF files are not supported.",
            MessageSeverity.WARNING,
            "Use an unencrypted local copy.",
        )
    if isinstance(error, NoExtractableTextError):
        return UiMessage(
            "No readable text",
            "No readable text could be extracted. OCR is not supported in this version.",
            MessageSeverity.WARNING,
            "Use a text-based PDF or another supported document format.",
        )
    if isinstance(error, CorruptDocumentError):
        return UiMessage(
            "Unreadable document",
            "The document appears to be corrupt or invalid.",
            MessageSeverity.ERROR,
            "Open the source file locally and export a fresh copy.",
        )
    if isinstance(error, EncodingError):
        return UiMessage(
            "Unsupported text encoding",
            "GroundNote could not read this text document as UTF-8.",
            MessageSeverity.WARNING,
            "Save the document as UTF-8 and try again.",
        )
    if isinstance(error, ParserNotFoundError):
        return UiMessage(
            "Document reader unavailable",
            "GroundNote does not have a reader for this document type.",
            MessageSeverity.ERROR,
        )
    if isinstance(error, DuplicateDocumentError):
        return UiMessage(
            "Document already added",
            "This document has already been added to GroundNote.",
            MessageSeverity.INFO,
        )
    if isinstance(error, ChunkingError):
        return UiMessage(
            "Document processing failed",
            "GroundNote could not create safe searchable sections for this document.",
            MessageSeverity.ERROR,
        )
    if isinstance(
        error,
        (EmbeddingModelLoadError, ChatModelLoadError, FoundryModelUnavailableError),
    ):
        return UiMessage(
            "Local model unavailable",
            "The required Foundry Local model could not be loaded.",
            MessageSeverity.ERROR,
            "Confirm the model is cached and run `foundry server start` in a terminal.",
        )
    if isinstance(error, (FoundryCatalogError, FoundryProviderError)):
        return UiMessage(
            "Foundry Local unavailable",
            "GroundNote could not reach the local AI runtime.",
            MessageSeverity.ERROR,
            "Run `foundry server start` in a terminal, then try again.",
        )
    if isinstance(error, (IndexingError, EmbeddingGenerationError)):
        return UiMessage(
            "Indexing failed",
            "The document was saved but its local search index could not be completed.",
            MessageSeverity.ERROR,
            "Check Foundry Local and review the document status before trying again later.",
        )
    if isinstance(error, EmbeddingError):
        return UiMessage(
            "Local embedding failed",
            "GroundNote could not complete the local embedding operation.",
            MessageSeverity.ERROR,
        )
    if isinstance(error, EmptyRagQueryError):
        return UiMessage(
            "Empty question",
            "Enter a question before asking GroundNote.",
            MessageSeverity.INFO,
        )
    if isinstance(error, NoIndexedDocumentsError):
        return UiMessage(
            "No indexed documents",
            "Add and index at least one document before asking a question.",
            MessageSeverity.INFO,
        )
    if isinstance(error, InvalidFilterError):
        return UiMessage(
            "Invalid source filter",
            "One or more selected sources are no longer available.",
            MessageSeverity.WARNING,
            "Refresh the page and choose indexed documents again.",
        )
    if isinstance(error, RagRetrievalError):
        return UiMessage(
            "Search failed",
            "GroundNote could not search the local document index.",
            MessageSeverity.ERROR,
        )
    if isinstance(error, (ChatGenerationError, InvalidChatResponseError)):
        return UiMessage(
            "Answer generation failed",
            "The local model could not produce a safe grounded answer.",
            MessageSeverity.ERROR,
            "Try a shorter or more specific question.",
        )
    if isinstance(error, CitationValidationError):
        return UiMessage(
            "Citation validation failed",
            "The answer was not shown because its sources could not be verified.",
            MessageSeverity.WARNING,
            "Try asking the question again.",
        )
    if isinstance(error, RagError):
        return UiMessage(
            "Question could not be completed",
            "The question could not be processed safely by the local RAG workflow.",
            MessageSeverity.WARNING,
            "Try a shorter or more specific question.",
        )
    if isinstance(error, DocumentError):
        return UiMessage(
            "Document processing failed",
            "GroundNote could not safely process this document.",
            MessageSeverity.ERROR,
        )
    if isinstance(error, (StorageError, MigrationError, DatabaseBootstrapError)):
        return UiMessage(
            "Local database unavailable",
            "GroundNote could not access its local document database.",
            MessageSeverity.ERROR,
            "Close other GroundNote windows and restart the application.",
        )
    return UiMessage(
        "Operation failed",
        "Something went wrong while completing this operation.",
        MessageSeverity.ERROR,
        "Try again. If the problem continues, restart GroundNote.",
    )
