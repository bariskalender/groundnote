"""Serialize NumPy embeddings to compact SQLite BLOB values."""

from __future__ import annotations

import numpy as np
import numpy.typing as npt

from groundnote.storage.exceptions import InvalidEmbeddingError

SUPPORTED_EMBEDDING_DTYPE = "float32"


def serialize_embedding(array: npt.ArrayLike) -> tuple[bytes, int, str]:
    """Serialize a one-dimensional finite vector as float32 bytes."""
    vector = np.asarray(array)
    if vector.ndim != 1:
        raise InvalidEmbeddingError("Embedding must be one-dimensional.")
    if vector.size == 0:
        raise InvalidEmbeddingError("Embedding must not be empty.")

    vector = np.ascontiguousarray(vector.astype(np.float32, copy=False))
    if not np.all(np.isfinite(vector)):
        raise InvalidEmbeddingError("Embedding contains non-finite values.")
    return vector.tobytes(), int(vector.shape[0]), SUPPORTED_EMBEDDING_DTYPE


def deserialize_embedding(
    data: bytes,
    *,
    expected_dimension: int,
    expected_dtype: str,
) -> npt.NDArray[np.float32]:
    """Deserialize a finite float32 vector from SQLite BLOB bytes."""
    if expected_dtype != SUPPORTED_EMBEDDING_DTYPE:
        raise InvalidEmbeddingError("Only float32 embeddings are supported.")
    if expected_dimension <= 0:
        raise InvalidEmbeddingError("Expected dimension must be positive.")

    expected_length = expected_dimension * np.dtype(np.float32).itemsize
    if len(data) != expected_length:
        raise InvalidEmbeddingError("Embedding BLOB length does not match expected dimension.")

    vector = np.frombuffer(data, dtype=np.float32).copy()
    if vector.shape != (expected_dimension,):
        raise InvalidEmbeddingError("Embedding dimension mismatch.")
    if not np.all(np.isfinite(vector)):
        raise InvalidEmbeddingError("Embedding contains non-finite values.")
    return vector
