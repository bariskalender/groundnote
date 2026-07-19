"""Semantic retrieval errors."""

from __future__ import annotations


class RetrievalError(Exception):
    """Base retrieval error."""


class EmptyQueryError(RetrievalError):
    """Raised when a semantic query is empty."""


class SimilarityError(RetrievalError):
    """Raised when similarity calculation cannot be performed safely."""
