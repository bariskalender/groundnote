"""Markdown parser using the Python standard library."""

from __future__ import annotations

import re
from pathlib import Path

from groundnote.documents.models import ParsedDocument, ParsedSection
from groundnote.documents.parsers.base import make_section, require_sections
from groundnote.documents.parsers.text import TextParser
from groundnote.domain import SupportedFileType

_HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*$")


class MarkdownParser:
    """Split Markdown by headings while preserving inert text and code blocks."""

    supported_file_type = SupportedFileType.MARKDOWN

    def validate_compatible(self, file_path: Path) -> None:
        TextParser._read_text(file_path)

    def parse(
        self,
        file_path: Path,
        *,
        original_filename: str,
        stored_filename: str,
        sha256: str,
        file_size_bytes: int,
    ) -> ParsedDocument:
        text = TextParser._read_text(file_path)
        sections = self._sections_from_markdown(text)
        require_sections(sections)
        return ParsedDocument(
            original_filename=original_filename,
            stored_filename=stored_filename,
            file_type=self.supported_file_type,
            sha256=sha256,
            file_size_bytes=file_size_bytes,
            page_count=None,
            sections=sections,
            warnings=[],
        )

    @staticmethod
    def _sections_from_markdown(text: str) -> list[ParsedSection]:
        sections: list[ParsedSection] = []
        current_title: str | None = None
        buffer: list[str] = []
        in_code = False
        order = 0

        def flush() -> None:
            nonlocal buffer, order
            section = make_section(
                "\n".join(buffer),
                source_order=order,
                section_title=current_title,
            )
            if section is not None:
                sections.append(section)
                order += 1
            buffer = []

        for line in text.splitlines():
            stripped = line.strip()
            if stripped.startswith("```") or stripped.startswith("~~~"):
                in_code = not in_code
                buffer.append(line)
                continue
            match = _HEADING_RE.match(line) if not in_code else None
            if match is not None:
                flush()
                current_title = match.group(2).strip()
                buffer.append(line)
            else:
                buffer.append(line)
        flush()
        return sections
