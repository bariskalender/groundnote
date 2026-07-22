"""Parser registry for supported document types."""

from __future__ import annotations

from dataclasses import dataclass

from groundnote.config import Settings
from groundnote.documents.errors import ParserNotFoundError
from groundnote.documents.interfaces import DocumentParser
from groundnote.documents.parsers import DocxParser, MarkdownParser, PdfParser, TextParser
from groundnote.domain import SupportedFileType


@dataclass(frozen=True)
class ParserRegistry:
    """Immutable parser registry."""

    parsers: dict[SupportedFileType, DocumentParser]

    def get(self, file_type: SupportedFileType) -> DocumentParser:
        try:
            return self.parsers[file_type]
        except KeyError as exc:
            raise ParserNotFoundError() from exc


def default_parser_registry(settings: Settings | None = None) -> ParserRegistry:
    """Create the default Phase 3 parser registry."""
    extracted_limit = settings.maximum_extracted_characters if settings else 5_000_000
    parsers: list[DocumentParser] = [
        PdfParser(
            maximum_pages=settings.maximum_pdf_pages if settings else 1_000,
            maximum_extracted_characters=extracted_limit,
        ),
        DocxParser(
            maximum_expanded_size_bytes=(
                settings.docx_maximum_expanded_size_mb * 1024 * 1024
                if settings
                else 200 * 1024 * 1024
            ),
            maximum_compression_ratio=(
                settings.docx_maximum_compression_ratio if settings else 100.0
            ),
            maximum_member_size_bytes=(
                settings.docx_maximum_member_size_mb * 1024 * 1024 if settings else 50 * 1024 * 1024
            ),
            maximum_members=settings.docx_maximum_members if settings else 2_000,
            maximum_extracted_characters=extracted_limit,
        ),
        TextParser(maximum_extracted_characters=extracted_limit),
        MarkdownParser(maximum_extracted_characters=extracted_limit),
    ]
    return ParserRegistry({parser.supported_file_type: parser for parser in parsers})
