"""Unit tests for Foundry embedding provider local-service helpers."""

from __future__ import annotations

import subprocess
from typing import Any

import pytest

from groundnote.ai.errors import FoundryProviderError
from groundnote.ai.foundry_embeddings import FoundryEmbeddingProvider


class FallbackModel:
    id = "embedding-test-model:1"
    is_loaded = False

    def load(self) -> None:
        raise RuntimeError("direct load failed")


class FallbackManager:
    def __init__(self) -> None:
        self.model = FallbackModel()

    def get_model(self, _alias: str) -> Any:
        return self.model


def test_local_service_base_url_uses_loopback_only(monkeypatch: pytest.MonkeyPatch) -> None:
    """The local daemon fallback must not accept a non-local service URL."""

    def fake_run_foundry(
        arguments: list[str],
        *,
        timeout_seconds: int,
        check: bool = True,
    ) -> subprocess.CompletedProcess[str]:
        assert arguments == ["server", "status"]
        assert timeout_seconds == 30
        assert check is True
        return subprocess.CompletedProcess(
            args=["foundry", *arguments],
            returncode=0,
            stdout="Web URLs http://127.0.0.1:50377",
            stderr="",
        )

    monkeypatch.setattr(
        FoundryEmbeddingProvider,
        "_run_foundry",
        staticmethod(fake_run_foundry),
    )

    assert FoundryEmbeddingProvider._local_service_base_url() == "http://127.0.0.1:50377"


def test_local_service_base_url_rejects_missing_loopback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A malformed or non-local daemon status should fail closed."""

    def fake_run_foundry(
        arguments: list[str],
        *,
        timeout_seconds: int,
        check: bool = True,
    ) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(
            args=["foundry", *arguments],
            returncode=0,
            stdout="Web URLs http://192.0.2.10:50377",
            stderr="",
        )

    monkeypatch.setattr(FoundryEmbeddingProvider, "_run_foundry", fake_run_foundry)

    with pytest.raises(FoundryProviderError):
        FoundryEmbeddingProvider._local_service_base_url()


def test_fallback_setup_failure_unloads_newly_loaded_model(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[list[str]] = []

    def fake_run_foundry(
        arguments: list[str],
        *,
        timeout_seconds: int,
        check: bool = True,
    ) -> subprocess.CompletedProcess[str]:
        del timeout_seconds, check
        calls.append(arguments)
        output = "Server status did not include an endpoint"
        return subprocess.CompletedProcess(arguments, 0, output, "")

    monkeypatch.setattr(
        FoundryEmbeddingProvider,
        "_run_foundry",
        staticmethod(fake_run_foundry),
    )
    provider = FoundryEmbeddingProvider("embedding-test", manager=FallbackManager())

    with pytest.raises(FoundryProviderError):
        provider.load()

    assert ["model", "load", "embedding-test-model:1"] in calls
    assert ["model", "unload", "embedding-test-model:1"] in calls
