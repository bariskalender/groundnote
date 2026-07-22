"""PDF parser backed by pypdf."""

from __future__ import annotations

from pathlib import Path
from typing import BinaryIO

from pypdf import PdfReader
from pypdf.errors import PdfReadError

from groundnote.documents.errors import (
    CorruptDocumentError,
    EncryptedDocumentError,
    ExtractedTextLimitError,
    PdfPageLimitError,
)
from groundnote.documents.models import ParsedDocument, ParsedSection
from groundnote.documents.parsers.base import make_section, require_sections
from groundnote.domain import SupportedFileType


class PdfParser:
    """Extract PDF text page by page without OCR."""

    supported_file_type = SupportedFileType.PDF

    def __init__(
        self,
        *,
        maximum_pages: int = 1_000,
        maximum_extracted_characters: int = 5_000_000,
    ) -> None:
        self.maximum_pages = maximum_pages
        self.maximum_extracted_characters = maximum_extracted_characters

    def validate_compatible(self, file_path: Path) -> None:
        with file_path.open("rb") as source:
            reader = self._reader(source)
            self._validate_page_count(reader)

    def parse(
        self,
        file_path: Path,
        *,
        original_filename: str,
        stored_filename: str,
        sha256: str,
        file_size_bytes: int,
    ) -> ParsedDocument:
        sections: list[ParsedSection] = []
        warnings: list[str] = []
        try:
            with file_path.open("rb") as source:
                reader = self._reader(source)
                page_count = self._validate_page_count(reader)
                blank_pages = 0
                extracted_characters = 0
                for index, page in enumerate(reader.pages, start=1):
                    try:
                        text = page.extract_text() or ""
                    except Exception:
                        text = ""
                        warnings.append(f"Page {index} could not be extracted.")
                    extracted_characters += len(text)
                    if extracted_characters > self.maximum_extracted_characters:
                        raise ExtractedTextLimitError()
                    section = make_section(text, source_order=index - 1, page_number=index)
                    text = ""
                    if section is None:
                        blank_pages += 1
                        warnings.append(f"Page {index} contains no extractable text.")
                    else:
                        sections.append(section)
        except (EncryptedDocumentError, ExtractedTextLimitError, PdfPageLimitError):
            raise
        except (PdfReadError, OSError, ValueError) as exc:
            raise CorruptDocumentError() from exc
        require_sections(sections, scanned_hint=page_count > 0 and blank_pages == page_count)
        if blank_pages and blank_pages >= max(1, page_count - 1):
            warnings.append("The document may be scanned or image-only; OCR is not supported.")
        return ParsedDocument(
            original_filename=original_filename,
            stored_filename=stored_filename,
            file_type=self.supported_file_type,
            sha256=sha256,
            file_size_bytes=file_size_bytes,
            page_count=page_count,
            sections=sections,
            warnings=warnings,
        )

    def _validate_page_count(self, reader: PdfReader) -> int:
        page_count = len(reader.pages)
        if page_count > self.maximum_pages:
            raise PdfPageLimitError()
        return page_count

    @staticmethod
    def _reader(source: BinaryIO) -> PdfReader:
        try:
            reader = PdfReader(source)
            if reader.is_encrypted:
                raise EncryptedDocumentError()
            return reader
        except EncryptedDocumentError:
            raise
        except (PdfReadError, OSError, ValueError) as exc:
            raise CorruptDocumentError() from exc
