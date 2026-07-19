"""PDF parser backed by pypdf."""

from __future__ import annotations

from pathlib import Path

from pypdf import PdfReader
from pypdf.errors import PdfReadError

from groundnote.documents.errors import CorruptDocumentError, EncryptedDocumentError
from groundnote.documents.models import ParsedDocument, ParsedSection
from groundnote.documents.parsers.base import make_section, require_sections
from groundnote.domain import SupportedFileType


class PdfParser:
    """Extract PDF text page by page without OCR."""

    supported_file_type = SupportedFileType.PDF

    def validate_compatible(self, file_path: Path) -> None:
        self._reader(file_path)

    def parse(
        self,
        file_path: Path,
        *,
        original_filename: str,
        stored_filename: str,
        sha256: str,
        file_size_bytes: int,
    ) -> ParsedDocument:
        reader = self._reader(file_path)
        sections: list[ParsedSection] = []
        warnings: list[str] = []
        page_count = len(reader.pages)
        blank_pages = 0
        for index, page in enumerate(reader.pages, start=1):
            try:
                text = page.extract_text() or ""
            except Exception:
                text = ""
                warnings.append(f"Page {index} could not be extracted.")
            section = make_section(text, source_order=index - 1, page_number=index)
            if section is None:
                blank_pages += 1
                warnings.append(f"Page {index} contains no extractable text.")
            else:
                sections.append(section)
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

    @staticmethod
    def _reader(file_path: Path) -> PdfReader:
        try:
            reader = PdfReader(file_path)
            if reader.is_encrypted:
                raise EncryptedDocumentError()
            return reader
        except EncryptedDocumentError:
            raise
        except (PdfReadError, OSError, ValueError) as exc:
            raise CorruptDocumentError() from exc
