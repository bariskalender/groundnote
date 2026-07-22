from __future__ import annotations

import subprocess
from typing import Any

import pytest

from groundnote.ai.errors import FoundryProviderError
from groundnote.ai.foundry_chat import FoundryChatProvider


class ClientFailModel:
    id = "chat-test-model:1"

    def __init__(self, *, initially_loaded: bool = False) -> None:
        self.is_loaded = initially_loaded
        self.unload_calls = 0

    def load(self) -> None:
        self.is_loaded = True

    def unload(self) -> None:
        self.unload_calls += 1
        self.is_loaded = False

    def get_chat_client(self) -> Any:
        raise RuntimeError("client creation failed")


class ModelManager:
    def __init__(self, model: ClientFailModel) -> None:
        self.model = model

    def get_model(self, _alias: str) -> Any:
        return self.model


def test_direct_client_creation_failure_rolls_back_owned_model(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    model = ClientFailModel()

    def fail_fallback(
        arguments: list[str],
        *,
        timeout_seconds: int,
        check: bool = True,
    ) -> subprocess.CompletedProcess[str]:
        del arguments, timeout_seconds, check
        raise RuntimeError("fallback unavailable")

    monkeypatch.setattr(FoundryChatProvider, "_run_foundry", staticmethod(fail_fallback))
    provider = FoundryChatProvider("chat-test", manager=ModelManager(model))

    with pytest.raises(FoundryProviderError):
        provider.load()

    assert model.unload_calls == 1
    assert model.is_loaded is False


def test_fallback_endpoint_failure_unloads_newly_loaded_model(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    model = ClientFailModel()
    calls: list[list[str]] = []

    def fake_run_foundry(
        arguments: list[str],
        *,
        timeout_seconds: int,
        check: bool = True,
    ) -> subprocess.CompletedProcess[str]:
        del timeout_seconds, check
        calls.append(arguments)
        return subprocess.CompletedProcess(arguments, 0, "endpoint unavailable", "")

    monkeypatch.setattr(FoundryChatProvider, "_run_foundry", staticmethod(fake_run_foundry))
    provider = FoundryChatProvider("chat-test", manager=ModelManager(model))

    with pytest.raises(FoundryProviderError):
        provider.load()

    assert ["model", "load", model.id] in calls
    assert ["model", "unload", model.id] in calls


def test_preloaded_external_model_is_not_unloaded_on_failed_client_creation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    model = ClientFailModel(initially_loaded=True)

    def fail_fallback(
        arguments: list[str],
        *,
        timeout_seconds: int,
        check: bool = True,
    ) -> subprocess.CompletedProcess[str]:
        del arguments, timeout_seconds, check
        raise RuntimeError("fallback unavailable")

    monkeypatch.setattr(FoundryChatProvider, "_run_foundry", staticmethod(fail_fallback))
    provider = FoundryChatProvider("chat-test", manager=ModelManager(model))

    with pytest.raises(FoundryProviderError):
        provider.load()

    assert model.unload_calls == 0
