"""Document chunking package."""

from groundnote.chunking.errors import (
    ChunkingError,
    ChunkMetadataError,
    ChunkSizeError,
    EmptyChunkError,
    InvalidChunkSettingsError,
)
from groundnote.chunking.hybrid_recursive import HybridRecursiveChunker
from groundnote.chunking.interfaces import DocumentChunker
from groundnote.chunking.models import (
    ChunkCandidate,
    ChunkingResult,
    ChunkingSettings,
    IngestionPlan,
    TextChunk,
)
from groundnote.chunking.service import estimate_tokens, settings_to_chunking_settings

__all__ = [
    "ChunkCandidate",
    "ChunkMetadataError",
    "ChunkSizeError",
    "ChunkingError",
    "ChunkingResult",
    "ChunkingSettings",
    "DocumentChunker",
    "EmptyChunkError",
    "HybridRecursiveChunker",
    "IngestionPlan",
    "InvalidChunkSettingsError",
    "TextChunk",
    "estimate_tokens",
    "settings_to_chunking_settings",
]
