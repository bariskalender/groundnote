from __future__ import annotations

from pathlib import Path

import pytest

from groundnote.ai import FoundryProviderError
from groundnote.documents import (
    CorruptDocumentError,
    DocxArchiveSafetyError,
    DuplicateDocumentError,
    EncryptedDocumentError,
    ExtractedTextLimitError,
    FileTooLargeError,
    NoExtractableTextError,
    PdfPageLimitError,
    UnsupportedFileTypeError,
)
from groundnote.embeddings import IndexingError
from groundnote.rag import ChatGenerationError, CitationValidationError
from groundnote.ui.errors import MessageSeverity, map_exception


@pytest.mark.parametrize(
    ("error", "title", "severity"),
    [
        (UnsupportedFileTypeError(), "Unsupported file type", MessageSeverity.WARNING),
        (FileTooLargeError(), "File is too large", MessageSeverity.WARNING),
        (DuplicateDocumentError(), "Document already added", MessageSeverity.INFO),
        (EncryptedDocumentError(), "Encrypted PDF", MessageSeverity.WARNING),
        (NoExtractableTextError(), "No readable text", MessageSeverity.WARNING),
        (CorruptDocumentError(), "Unreadable document", MessageSeverity.ERROR),
        (PdfPageLimitError(), "PDF page limit exceeded", MessageSeverity.WARNING),
        (ExtractedTextLimitError(), "Extracted text limit exceeded", MessageSeverity.WARNING),
        (DocxArchiveSafetyError(), "Unsafe DOCX archive", MessageSeverity.WARNING),
        (FoundryProviderError("internal"), "Foundry Local unavailable", MessageSeverity.ERROR),
        (IndexingError("internal"), "Indexing failed", MessageSeverity.ERROR),
        (ChatGenerationError("internal"), "Answer generation failed", MessageSeverity.ERROR),
        (
            CitationValidationError("internal"),
            "Citation validation failed",
            MessageSeverity.WARNING,
        ),
    ],
)
def test_expected_errors_have_safe_mappings(
    error: BaseException,
    title: str,
    severity: MessageSeverity,
) -> None:
    message = map_exception(error)

    assert message.title == title
    assert message.severity is severity
    assert "internal" not in message.message


def test_unexpected_error_never_leaks_path_or_stack_details(tmp_path: Path) -> None:
    private = tmp_path / "private" / "secret.pdf"
    error = RuntimeError(f"failed at {private}\nTraceback: SQL SELECT * FROM documents")

    message = map_exception(error)
    rendered = f"{message.title} {message.message} {message.remediation}"

    assert str(tmp_path) not in rendered
    assert "Traceback" not in rendered
    assert "SELECT" not in rendered
    assert message.message == (
        "Something went wrong while completing the operation. "
        "The state was reset, so you can try again."
    )


def test_unexpected_error_has_localized_reset_message() -> None:
    message = map_exception(RuntimeError("private internal detail"), "tr")

    assert message.message == (
        "İşlem sırasında bir sorun oluştu. Durum sıfırlandı; tekrar deneyebilirsiniz."
    )
    assert "private internal detail" not in message.message


def test_no_extractable_text_uses_image_only_pdf_message() -> None:
    english = map_exception(NoExtractableTextError(), "en")
    turkish = map_exception(NoExtractableTextError(), "tr")

    assert "image-based" in english.message
    assert "OCR" in english.message
    assert "görüntü tabanlı" in turkish.message
