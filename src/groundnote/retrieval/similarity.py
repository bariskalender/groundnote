"""NumPy cosine similarity helpers."""

from __future__ import annotations

from typing import cast

import numpy as np
import numpy.typing as npt

from groundnote.retrieval.errors import SimilarityError


def cosine_similarity_scores(
    query_vector: npt.ArrayLike,
    candidate_matrix: npt.ArrayLike,
    *,
    normalized: bool = True,
) -> npt.NDArray[np.float32]:
    """Return deterministic cosine scores for one query and many candidates."""
    query = np.asarray(query_vector, dtype=np.float32)
    candidates = np.asarray(candidate_matrix, dtype=np.float32)
    if query.ndim != 1:
        raise SimilarityError("Query vector must be one-dimensional.")
    if candidates.ndim != 2:
        raise SimilarityError("Candidate matrix must be two-dimensional.")
    if candidates.shape[1] != query.shape[0]:
        raise SimilarityError("Query and candidate dimensions do not match.")
    if candidates.shape[0] == 0:
        return np.asarray([], dtype=np.float32)
    if not np.all(np.isfinite(query)) or not np.all(np.isfinite(candidates)):
        raise SimilarityError("Similarity inputs must be finite.")
    if normalized:
        _validate_normalized(query)
        for row in candidates:
            _validate_normalized(row)
        return cast(
            npt.NDArray[np.float32],
            np.dot(candidates, query).astype(np.float32, copy=False),
        )

    query_norm = float(np.linalg.norm(query))
    candidate_norms = np.linalg.norm(candidates, axis=1)
    if query_norm <= 0.0 or not np.isfinite(query_norm):
        raise SimilarityError("Query vector norm must be positive.")
    if not np.all(np.isfinite(candidate_norms)) or np.any(candidate_norms <= 0.0):
        raise SimilarityError("Candidate vector norms must be positive.")
    return cast(
        npt.NDArray[np.float32],
        (np.dot(candidates, query) / (candidate_norms * query_norm)).astype(np.float32),
    )


def _validate_normalized(vector: npt.NDArray[np.float32]) -> None:
    norm = float(np.linalg.norm(vector))
    if not np.isfinite(norm) or norm <= 0.0:
        raise SimilarityError("Vector norm must be positive.")
