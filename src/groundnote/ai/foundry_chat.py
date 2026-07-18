"""Foundry Local chat provider."""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from typing import Any, cast

from groundnote.ai.errors import FoundryProviderError
from groundnote.ai.foundry_manager import FoundryManager
from groundnote.ai.models import ChatMessage, ChatResult, ModelInfo


class FoundryChatProvider:
    """Chat provider backed by Microsoft Foundry Local."""

    def __init__(self, model_alias: str, manager: FoundryManager | None = None) -> None:
        self.model_alias = model_alias
        self._manager = manager or FoundryManager()
        self._model: Any | None = None
        self._client: Any | None = None

    def ensure_model_available(self, *, download: bool = False) -> ModelInfo:
        model = self._manager.get_model(self.model_alias)
        if download and not bool(getattr(model, "is_cached", False)):
            model.download()
        return self._manager.get_model_info(self.model_alias)

    def load(self) -> None:
        try:
            self._model = self._manager.get_model(self.model_alias)
            self._model.load()
            self._client = self._model.get_chat_client()
        except Exception as exc:
            raise FoundryProviderError(f"Could not load chat model: {self.model_alias}") from exc

    def generate(self, messages: Sequence[ChatMessage], *, max_tokens: int = 64) -> ChatResult:
        client = self._require_client()
        self._configure_client(client, max_tokens=max_tokens)
        request_messages = [self._message_to_dict(message) for message in messages]
        try:
            response = client.complete_chat(request_messages)
            text = response.choices[0].message.content
        except Exception as exc:
            raise FoundryProviderError("Foundry Local chat generation failed.") from exc
        return ChatResult(text=str(text or ""), model_alias=self.model_alias)

    def stream(self, messages: Sequence[ChatMessage], *, max_tokens: int = 64) -> Iterable[str]:
        client = self._require_client()
        self._configure_client(client, max_tokens=max_tokens)
        request_messages = [self._message_to_dict(message) for message in messages]
        try:
            chunks = client.complete_streaming_chat(request_messages)
            for chunk in chunks:
                if not chunk.choices:
                    continue
                content = chunk.choices[0].delta.content
                if content:
                    yield str(content)
        except Exception as exc:
            raise FoundryProviderError("Foundry Local streaming chat generation failed.") from exc

    def unload(self) -> None:
        if self._model is None:
            return
        try:
            self._model.unload()
        except Exception as exc:
            raise FoundryProviderError(f"Could not unload chat model: {self.model_alias}") from exc
        finally:
            self._client = None
            self._model = None

    def _require_client(self) -> Any:
        if self._client is None:
            raise FoundryProviderError("Chat model is not loaded.")
        return self._client

    @staticmethod
    def _configure_client(client: Any, *, max_tokens: int) -> None:
        settings = getattr(client, "settings", None)
        if settings is not None:
            settings.max_tokens = max_tokens
            settings.temperature = 0.0

    @staticmethod
    def _message_to_dict(message: ChatMessage) -> dict[str, str]:
        return cast(dict[str, str], {"role": message.role, "content": message.content})
