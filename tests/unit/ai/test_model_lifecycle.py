from __future__ import annotations

from collections.abc import Sequence

import pytest

from groundnote.ai.fakes import FakeChatProvider
from groundnote.ai.lifecycle import ChatModelLifecycle
from groundnote.ai.models import ChatGenerationRequest, ChatGenerationResult


class TrackingChatProvider(FakeChatProvider):
    def __init__(
        self,
        model_alias: str,
        *,
        fail_load: bool = False,
        fail_generation: bool = False,
    ) -> None:
        super().__init__(model_alias=model_alias)
        self.fail_load = fail_load
        self.fail_generation = fail_generation
        self.load_calls = 0
        self.unload_calls = 0

    def load(self) -> None:
        self.load_calls += 1
        if self.fail_load:
            raise RuntimeError("synthetic load failure")
        super().load()

    def unload(self) -> None:
        self.unload_calls += 1
        super().unload()

    def generate_request(self, request: ChatGenerationRequest) -> ChatGenerationResult:
        if self.fail_generation:
            raise RuntimeError("synthetic generation failure")
        return super().generate_request(request)


def _request(model: str) -> ChatGenerationRequest:
    return ChatGenerationRequest(
        system_prompt="system",
        user_prompt="user",
        temperature=0.0,
        max_output_tokens=8,
        model=model,
    )


@pytest.mark.parametrize("order", [("fast", "balanced"), ("balanced", "fast")])
def test_switching_models_never_keeps_two_owned_chat_providers_loaded(
    order: Sequence[str],
) -> None:
    lifecycle = ChatModelLifecycle()
    raw = {
        "fast": TrackingChatProvider("fast"),
        "balanced": TrackingChatProvider("balanced"),
    }
    managed = {name: lifecycle.register(provider) for name, provider in raw.items()}

    for name in order:
        managed[name].load()
        managed[name].generate_request(_request(name))
        assert sum(provider.loaded for provider in raw.values()) == 1
        assert lifecycle.active_model_alias == name


def test_repeated_same_model_reuses_one_provider_load() -> None:
    lifecycle = ChatModelLifecycle()
    raw = TrackingChatProvider("balanced")
    managed = lifecycle.register(raw)

    managed.load()
    managed.generate_request(_request("balanced"))
    managed.load()
    managed.generate_request(_request("balanced"))

    assert raw.load_calls == 1
    assert raw.unload_calls == 0
    assert raw.loaded is True


def test_switch_load_failure_leaves_no_partially_active_new_model() -> None:
    lifecycle = ChatModelLifecycle()
    first = TrackingChatProvider("balanced")
    failing = TrackingChatProvider("fast", fail_load=True)
    managed_first = lifecycle.register(first)
    managed_failing = lifecycle.register(failing)
    managed_first.load()

    with pytest.raises(RuntimeError, match="synthetic load failure"):
        managed_failing.load()

    assert first.loaded is False
    assert failing.loaded is False
    assert lifecycle.active_model_alias is None


def test_generation_failure_releases_active_model() -> None:
    lifecycle = ChatModelLifecycle()
    failing = TrackingChatProvider("balanced", fail_generation=True)
    managed = lifecycle.register(failing)
    managed.load()

    with pytest.raises(RuntimeError, match="synthetic generation failure"):
        managed.generate_request(_request("balanced"))

    assert failing.loaded is False
    assert lifecycle.active_model_alias is None


def test_shutdown_is_idempotent_and_releases_registered_providers() -> None:
    lifecycle = ChatModelLifecycle()
    raw = TrackingChatProvider("balanced")
    managed = lifecycle.register(raw)
    managed.load()

    assert lifecycle.shutdown() == []
    assert lifecycle.shutdown() == []
    assert raw.loaded is False
    assert lifecycle.active_model_alias is None
