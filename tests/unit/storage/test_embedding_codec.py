from __future__ import annotations

import numpy as np
import pytest

from groundnote.storage import deserialize_embedding, serialize_embedding
from groundnote.storage.exceptions import InvalidEmbeddingError


def test_float32_round_trip() -> None:
    source = np.array([1.0, 2.0, 3.0], dtype=np.float32)

    data, dimension, dtype = serialize_embedding(source)
    restored = deserialize_embedding(data, expected_dimension=dimension, expected_dtype=dtype)

    assert restored.dtype == np.float32
    assert np.allclose(restored, source)


def test_float64_and_non_contiguous_convert_to_float32() -> None:
    source = np.array([[1.0, 2.0], [3.0, 4.0]], dtype=np.float64).T[0]

    data, dimension, dtype = serialize_embedding(source)
    restored = deserialize_embedding(data, expected_dimension=dimension, expected_dtype=dtype)

    assert restored.dtype == np.float32
    assert restored.flags.c_contiguous


@pytest.mark.parametrize(
    "array",
    [
        np.array([], dtype=np.float32),
        np.array([[1.0]], dtype=np.float32),
        np.array([np.nan], dtype=np.float32),
        np.array([np.inf], dtype=np.float32),
    ],
)
def test_serialize_rejects_invalid_arrays(array: np.ndarray) -> None:
    with pytest.raises(InvalidEmbeddingError):
        serialize_embedding(array)


def test_deserialize_rejects_bad_metadata() -> None:
    data, dimension, dtype = serialize_embedding(np.array([1.0, 2.0], dtype=np.float32))

    with pytest.raises(InvalidEmbeddingError):
        deserialize_embedding(data, expected_dimension=dimension + 1, expected_dtype=dtype)
    with pytest.raises(InvalidEmbeddingError):
        deserialize_embedding(data, expected_dimension=dimension, expected_dtype="float64")
    with pytest.raises(InvalidEmbeddingError):
        deserialize_embedding(data[:-1], expected_dimension=dimension, expected_dtype=dtype)
