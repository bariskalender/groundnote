"""Explicit ownership for GroundNote-managed local chat providers."""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from contextlib import suppress
from threading import RLock

from groundnote.ai.interfaces import ChatProvider
from groundnote.ai.models import (
    ChatGenerationRequest,
    ChatGenerationResult,
    ChatMessage,
    ChatResult,
    ModelInfo,
)


class ChatModelLifecycle:
    """Keep at most one GroundNote-owned chat provider active at a time."""

    def __init__(self) -> None:
        self._active: ChatProvider | None = None
        self._owned: list[ChatProvider] = []
        self._lock = RLock()

    @property
    def active_model_alias(self) -> str | None:
        with self._lock:
            return self._active.model_alias if self._active is not None else None

    def register(self, provider: ChatProvider) -> ManagedChatProvider:
        with self._lock:
            if all(existing is not provider for existing in self._owned):
                self._owned.append(provider)
        return ManagedChatProvider(provider=provider, lifecycle=self)

    def activate(self, provider: ChatProvider) -> None:
        with self._lock:
            if self._active is provider:
                return
            if self._active is not None:
                previous = self._active
                try:
                    previous.unload()
                finally:
                    self._active = None
            try:
                provider.load()
            except Exception:
                with suppress(Exception):
                    provider.unload()
                raise
            self._active = provider

    def release(self, provider: ChatProvider) -> None:
        with self._lock:
            if self._active is not provider:
                return
            try:
                provider.unload()
            finally:
                self._active = None

    def shutdown(self) -> list[str]:
        """Best-effort release of every provider created and owned by GroundNote."""
        warnings: list[str] = []
        with self._lock:
            for provider in self._owned:
                try:
                    provider.unload()
                except Exception:
                    warnings.append(f"chat_unload_failed:{provider.model_alias}")
            self._active = None
        return warnings


class ManagedChatProvider:
    """Provider-neutral wrapper governed by a shared chat lifecycle."""

    def __init__(self, *, provider: ChatProvider, lifecycle: ChatModelLifecycle) -> None:
        self._provider = provider
        self._lifecycle = lifecycle
        self.model_alias = provider.model_alias

    def ensure_model_available(self, *, download: bool = False) -> ModelInfo:
        return self._provider.ensure_model_available(download=download)

    def load(self) -> None:
        self._lifecycle.activate(self._provider)

    def generate(self, messages: Sequence[ChatMessage], *, max_tokens: int = 64) -> ChatResult:
        try:
            return self._provider.generate(messages, max_tokens=max_tokens)
        except BaseException:
            self._release_after_failure()
            raise

    def generate_request(self, request: ChatGenerationRequest) -> ChatGenerationResult:
        try:
            return self._provider.generate_request(request)
        except BaseException:
            self._release_after_failure()
            raise

    def stream(self, messages: Sequence[ChatMessage], *, max_tokens: int = 64) -> Iterable[str]:
        try:
            yield from self._provider.stream(messages, max_tokens=max_tokens)
        except BaseException:
            self._release_after_failure()
            raise

    def unload(self) -> None:
        self._lifecycle.release(self._provider)

    def _release_after_failure(self) -> None:
        with suppress(Exception):
            self._lifecycle.release(self._provider)
