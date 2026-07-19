"""Document parser contracts."""

from __future__ import annotations

from pathlib import Path
from typing import Protocol

from groundnote.documents.models import ParsedDocument
from groundnote.domain import SupportedFileType


class DocumentParser(Protocol):
    """Parser contract for one supported document type."""

    supported_file_type: SupportedFileType

    def validate_compatible(self, file_path: Path) -> None:
        """Raise a document error if the file is incompatible with this parser."""

    def parse(
        self,
        file_path: Path,
        *,
        original_filename: str,
        stored_filename: str,
        sha256: str,
        file_size_bytes: int,
    ) -> ParsedDocument:
        """Parse a safe local file into text sections."""
