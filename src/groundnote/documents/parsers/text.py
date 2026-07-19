"""Plain text parser."""

from __future__ import annotations

from pathlib import Path

from groundnote.documents.errors import EncodingError
from groundnote.documents.models import ParsedDocument
from groundnote.documents.parsers.base import make_section, require_sections
from groundnote.documents.validation import is_binary_looking
from groundnote.domain import SupportedFileType


class TextParser:
    """Parse UTF-8 and UTF-8-BOM text files conservatively."""

    supported_file_type = SupportedFileType.TXT

    def validate_compatible(self, file_path: Path) -> None:
        self._read_text(file_path)

    def parse(
        self,
        file_path: Path,
        *,
        original_filename: str,
        stored_filename: str,
        sha256: str,
        file_size_bytes: int,
    ) -> ParsedDocument:
        text = self._read_text(file_path)
        section = make_section(text, source_order=0)
        if section is None:
            require_sections([])
            raise AssertionError("unreachable")
        return ParsedDocument(
            original_filename=original_filename,
            stored_filename=stored_filename,
            file_type=self.supported_file_type,
            sha256=sha256,
            file_size_bytes=file_size_bytes,
            page_count=None,
            sections=[section],
            warnings=[],
        )

    @staticmethod
    def _read_text(file_path: Path) -> str:
        data = file_path.read_bytes()
        if is_binary_looking(data[:4096]):
            raise EncodingError("The text file appears to contain binary data.")
        try:
            return data.decode("utf-8-sig")
        except UnicodeDecodeError as exc:
            raise EncodingError(
                "The text file must be UTF-8 encoded. Other encodings are not accepted yet."
            ) from exc
