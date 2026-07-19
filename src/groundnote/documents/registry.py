"""Parser registry for supported document types."""

from __future__ import annotations

from dataclasses import dataclass

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


def default_parser_registry() -> ParserRegistry:
    """Create the default Phase 3 parser registry."""
    parsers: list[DocumentParser] = [PdfParser(), DocxParser(), TextParser(), MarkdownParser()]
    return ParserRegistry({parser.supported_file_type: parser for parser in parsers})
