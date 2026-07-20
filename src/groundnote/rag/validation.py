"""RAG request validation."""

from __future__ import annotations

from groundnote.rag.errors import EmptyRagQueryError, RagError


def normalize_query(query: str, *, max_characters: int) -> str:
    """Normalize a user query without changing language or meaning."""
    normalized = query.replace("\r\n", "\n").replace("\r", "\n").replace("\x00", "").strip()
    if not normalized:
        raise EmptyRagQueryError("Question must not be empty.")
    if len(normalized) > max_characters:
        raise RagError("Question is too long for this local RAG request.")
    return normalized
