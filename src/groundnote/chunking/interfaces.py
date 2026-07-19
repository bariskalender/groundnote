"""Chunking provider contracts."""

from __future__ import annotations

from typing import Protocol

from groundnote.chunking.models import ChunkingResult, ChunkingSettings
from groundnote.documents import ParsedDocument


class DocumentChunker(Protocol):
    """Split a parsed document into ordered text chunks."""

    def chunk(
        self,
        document: ParsedDocument,
        settings: ChunkingSettings,
    ) -> ChunkingResult: ...
