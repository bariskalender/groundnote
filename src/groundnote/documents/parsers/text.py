"""Plain text parser."""

from __future__ import annotations

import codecs
from pathlib import Path

from groundnote.documents.errors import EncodingError, ExtractedTextLimitError
from groundnote.documents.models import ParsedDocument
from groundnote.documents.parsers.base import make_section, require_sections
from groundnote.documents.validation import is_binary_looking
from groundnote.domain import SupportedFileType


class TextParser:
    """Parse UTF-8 and UTF-8-BOM text files conservatively."""

    supported_file_type = SupportedFileType.TXT

    def __init__(self, *, maximum_extracted_characters: int = 5_000_000) -> None:
        self.maximum_extracted_characters = maximum_extracted_characters

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

    def _read_text(self, file_path: Path) -> str:
        decoder = codecs.getincrementaldecoder("utf-8-sig")("strict")
        parts: list[str] = []
        character_count = 0
        try:
            with file_path.open("rb") as source:
                first = source.read(64 * 1024)
                if is_binary_looking(first[:4096]):
                    raise EncodingError("The text file appears to contain binary data.")
                data = first
                while data:
                    decoded = decoder.decode(data, final=False)
                    character_count += len(decoded)
                    if character_count > self.maximum_extracted_characters:
                        raise ExtractedTextLimitError()
                    parts.append(decoded)
                    data = source.read(64 * 1024)
                tail = decoder.decode(b"", final=True)
                character_count += len(tail)
                if character_count > self.maximum_extracted_characters:
                    raise ExtractedTextLimitError()
                parts.append(tail)
        except UnicodeDecodeError as exc:
            raise EncodingError(
                "The text file must be UTF-8 encoded. Other encodings are not accepted yet."
            ) from exc
        return "".join(parts)
