"""Embedding validation and normalization helpers."""

from __future__ import annotations

import numpy as np
import numpy.typing as npt

from groundnote.embeddings.errors import (
    EmbeddingDimensionMismatchError,
    InvalidEmbeddingError,
    UnsupportedEmbeddingDtypeError,
)

SUPPORTED_DTYPE = "float32"


def validate_and_normalize_vector(
    values: npt.ArrayLike,
    *,
    expected_dimension: int,
    dtype: str = SUPPORTED_DTYPE,
) -> npt.NDArray[np.float32]:
    """Return a finite, one-dimensional, L2-normalized float32 vector."""
    if dtype != SUPPORTED_DTYPE:
        raise UnsupportedEmbeddingDtypeError("Only float32 embeddings are supported.")
    vector = np.asarray(values, dtype=np.float32)
    if vector.ndim != 1:
        raise InvalidEmbeddingError("Embedding vector must be one-dimensional.")
    if vector.shape[0] != expected_dimension:
        raise EmbeddingDimensionMismatchError("Embedding vector dimension mismatch.")
    if not np.all(np.isfinite(vector)):
        raise InvalidEmbeddingError("Embedding vector contains non-finite values.")
    norm = float(np.linalg.norm(vector))
    if not np.isfinite(norm) or norm <= 0.0:
        raise InvalidEmbeddingError("Embedding vector norm must be positive.")
    return (vector / norm).astype(np.float32, copy=False)


def validate_and_normalize_matrix(
    values: npt.ArrayLike,
    *,
    expected_dimension: int,
    expected_count: int,
    dtype: str = SUPPORTED_DTYPE,
) -> npt.NDArray[np.float32]:
    """Return a finite, row-normalized float32 matrix."""
    if dtype != SUPPORTED_DTYPE:
        raise UnsupportedEmbeddingDtypeError("Only float32 embeddings are supported.")
    matrix = np.asarray(values, dtype=np.float32)
    if matrix.ndim != 2:
        raise InvalidEmbeddingError("Embedding batch must be a two-dimensional matrix.")
    if matrix.shape != (expected_count, expected_dimension):
        raise EmbeddingDimensionMismatchError("Embedding batch shape mismatch.")
    rows = [
        validate_and_normalize_vector(row, expected_dimension=expected_dimension, dtype=dtype)
        for row in matrix
    ]
    return np.vstack(rows).astype(np.float32, copy=False)
