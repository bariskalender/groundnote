from __future__ import annotations

import numpy as np
import pytest

from groundnote.retrieval import SimilarityError, cosine_similarity_scores


def test_similarity_known_vectors_and_ranking() -> None:
    query = np.array([1.0, 0.0], dtype=np.float32)
    candidates = np.array(
        [
            [1.0, 0.0],
            [0.0, 1.0],
            [-1.0, 0.0],
        ],
        dtype=np.float32,
    )

    scores = cosine_similarity_scores(query, candidates)

    assert np.allclose(scores, np.array([1.0, 0.0, -1.0], dtype=np.float32))
    assert list(np.argsort(-scores)) == [0, 1, 2]


def test_similarity_rejects_malformed_inputs() -> None:
    with pytest.raises(SimilarityError):
        cosine_similarity_scores([1.0, 0.0], [[1.0, 0.0, 0.0]])
    with pytest.raises(SimilarityError):
        cosine_similarity_scores([0.0, 0.0], [[1.0, 0.0]])
    with pytest.raises(SimilarityError):
        cosine_similarity_scores([float("nan"), 0.0], [[1.0, 0.0]])
