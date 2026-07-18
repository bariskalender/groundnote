from __future__ import annotations

import numpy as np

from groundnote.ai.fakes import FakeChatProvider, FakeEmbeddingProvider
from groundnote.ai.models import ChatMessage


def test_fake_chat_provider_generates_after_load() -> None:
    provider = FakeChatProvider()
    provider.load()

    result = provider.generate([ChatMessage(role="user", content="hello")])

    assert result.text == "fake response: hello"
    assert result.model_alias == "fake-chat"


def test_fake_embedding_provider_returns_finite_float32_matrix() -> None:
    provider = FakeEmbeddingProvider(dimension=4)
    provider.load()

    result = provider.embed_many(["alpha", "beta"])

    assert result.vectors.shape == (2, 4)
    assert result.vectors.dtype == np.float32
    assert np.all(np.isfinite(result.vectors))
    assert result.dimension == 4
