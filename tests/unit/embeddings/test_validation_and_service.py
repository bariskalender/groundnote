from __future__ import annotations

import numpy as np
import pytest

from groundnote.ai.fakes import FakeEmbeddingProvider
from groundnote.config import Settings
from groundnote.embeddings import (
    EmbeddingDimensionMismatchError,
    EmbeddingGenerationError,
    EmbeddingService,
    EmptyEmbeddingInputError,
    InvalidEmbeddingError,
    validate_and_normalize_matrix,
    validate_and_normalize_vector,
)


def test_validate_vector_converts_to_normalized_float32() -> None:
    vector = validate_and_normalize_vector([3.0, 4.0], expected_dimension=2)

    assert vector.dtype == np.float32
    assert np.allclose(vector, np.array([0.6, 0.8], dtype=np.float32))


def test_validate_vector_rejects_bad_values() -> None:
    with pytest.raises(EmbeddingDimensionMismatchError):
        validate_and_normalize_vector([1.0], expected_dimension=2)
    with pytest.raises(InvalidEmbeddingError):
        validate_and_normalize_vector([float("nan"), 1.0], expected_dimension=2)
    with pytest.raises(InvalidEmbeddingError):
        validate_and_normalize_vector([float("inf"), 1.0], expected_dimension=2)
    with pytest.raises(InvalidEmbeddingError):
        validate_and_normalize_vector([0.0, 0.0], expected_dimension=2)


def test_validate_matrix_rejects_wrong_count_and_preserves_order() -> None:
    matrix = validate_and_normalize_matrix(
        [[1.0, 0.0], [0.0, 2.0]],
        expected_dimension=2,
        expected_count=2,
    )

    assert np.allclose(matrix[0], np.array([1.0, 0.0], dtype=np.float32))
    assert np.allclose(matrix[1], np.array([0.0, 1.0], dtype=np.float32))
    with pytest.raises(EmbeddingDimensionMismatchError):
        validate_and_normalize_matrix([[1.0, 0.0]], expected_dimension=2, expected_count=2)


def test_embedding_service_rejects_empty_inputs_and_preserves_batch_order() -> None:
    provider = FakeEmbeddingProvider(model_alias="qwen3-embedding-0.6b", dimension=4)
    settings = Settings(embedding_dimension=4, embedding_batch_size=2)
    service = EmbeddingService(settings=settings, provider=provider)
    service.load()

    result = service.embed_texts(["alpha", "beta", "gamma"])

    assert result.input_count == 3
    assert result.vectors.shape == (3, 4)
    assert all(np.isclose(np.linalg.norm(row), 1.0) for row in result.vectors)
    with pytest.raises(EmptyEmbeddingInputError):
        service.embed_texts([])
    with pytest.raises(EmptyEmbeddingInputError):
        service.embed_query("   ")


def test_embedding_service_maps_provider_failures() -> None:
    provider = FakeEmbeddingProvider(model_alias="qwen3-embedding-0.6b", dimension=4)
    settings = Settings(embedding_dimension=4)
    service = EmbeddingService(settings=settings, provider=provider)

    with pytest.raises(EmbeddingGenerationError):
        service.embed_texts(["not loaded"])
