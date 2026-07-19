"""Chunking error hierarchy."""

from __future__ import annotations


class ChunkingError(Exception):
    """Base class for safe chunking errors."""


class InvalidChunkSettingsError(ChunkingError):
    """Raised when chunking settings are internally inconsistent."""


class EmptyChunkError(ChunkingError):
    """Raised when a final chunk has no meaningful text."""


class ChunkSizeError(ChunkingError):
    """Raised when a chunk violates size constraints without a documented exception."""


class ChunkMetadataError(ChunkingError):
    """Raised when final chunk metadata is unsafe or incomplete."""
