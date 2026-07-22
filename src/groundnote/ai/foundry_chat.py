"""Foundry Local chat provider."""

from __future__ import annotations

import re
import shutil
import subprocess
import time
from collections.abc import Iterable, Sequence
from typing import Any, cast

from groundnote.ai.errors import FoundryProviderError
from groundnote.ai.foundry_manager import FoundryManager
from groundnote.ai.models import (
    ChatGenerationRequest,
    ChatGenerationResult,
    ChatMessage,
    ChatResult,
    ModelInfo,
)


class FoundryChatProvider:
    """Chat provider backed by Microsoft Foundry Local."""

    def __init__(self, model_alias: str, manager: FoundryManager | None = None) -> None:
        self.model_alias = model_alias
        self._manager = manager or FoundryManager()
        self._model: Any | None = None
        self._client: Any | None = None
        self._local_service_client: Any | None = None
        self._local_service_model_id: str | None = None
        self._direct_model_owned = False
        self._local_service_model_owned = False

    def ensure_model_available(self, *, download: bool = False) -> ModelInfo:
        model = self._manager.get_model(self.model_alias)
        if download and not bool(getattr(model, "is_cached", False)):
            model.download()
        return self._manager.get_model_info(self.model_alias)

    def load(self) -> None:
        if self._client is not None or self._local_service_client is not None:
            return
        try:
            self._model = self._manager.get_model(self.model_alias)
            self._direct_model_owned = not self._model_was_loaded(self._model)
            self._model.load()
            self._client = self._model.get_chat_client()
        except Exception:
            self._rollback_direct_load()
            try:
                self._load_via_local_service()
            except Exception as fallback_exc:
                self._rollback_local_service_load()
                raise FoundryProviderError(
                    f"Could not load chat model: {self.model_alias}"
                ) from fallback_exc

    def generate(self, messages: Sequence[ChatMessage], *, max_tokens: int = 64) -> ChatResult:
        try:
            text = self._generate_text(messages, max_tokens=max_tokens, temperature=0.0)
        except Exception as exc:
            raise FoundryProviderError("Foundry Local chat generation failed.") from exc
        return ChatResult(text=str(text or ""), model_alias=self.model_alias)

    def generate_request(self, request: ChatGenerationRequest) -> ChatGenerationResult:
        started = time.perf_counter()
        messages = [
            ChatMessage(role="system", content=request.system_prompt),
            ChatMessage(role="user", content=request.user_prompt),
        ]
        try:
            text = self._generate_text(
                messages,
                max_tokens=request.max_output_tokens,
                temperature=request.temperature,
            )
        except Exception as exc:
            raise FoundryProviderError("Foundry Local chat generation failed.") from exc
        return ChatGenerationResult(
            text=str(text or ""),
            model=request.model,
            duration_ms=round((time.perf_counter() - started) * 1000, 3),
        )

    def stream(self, messages: Sequence[ChatMessage], *, max_tokens: int = 64) -> Iterable[str]:
        client = self._require_client()
        self._configure_client(client, max_tokens=max_tokens, temperature=0.0)
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
        if self._local_service_model_id is not None:
            try:
                if self._local_service_model_owned:
                    self._unload_local_service_model()
            finally:
                self._clear_provider_state()
            return
        if self._model is not None:
            try:
                if self._direct_model_owned:
                    self._model.unload()
            except Exception as exc:
                raise FoundryProviderError(
                    f"Could not unload chat model: {self.model_alias}"
                ) from exc
            finally:
                self._clear_provider_state()

    def _generate_text(
        self,
        messages: Sequence[ChatMessage],
        *,
        max_tokens: int,
        temperature: float,
    ) -> str:
        request_messages = [self._message_to_dict(message) for message in messages]
        if self._local_service_client is not None:
            if self._local_service_model_id is None:
                raise FoundryProviderError("Local Foundry service chat model is not loaded.")
            response = self._local_service_client.chat.completions.create(
                model=self._local_service_model_id,
                messages=request_messages,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            return str(response.choices[0].message.content or "")

        client = self._require_client()
        self._configure_client(client, max_tokens=max_tokens, temperature=temperature)
        response = client.complete_chat(request_messages)
        return str(response.choices[0].message.content or "")

    def _require_client(self) -> Any:
        if self._client is None:
            raise FoundryProviderError("Chat model is not loaded.")
        return self._client

    @staticmethod
    def _configure_client(client: Any, *, max_tokens: int, temperature: float) -> None:
        settings = getattr(client, "settings", None)
        if settings is not None:
            settings.max_tokens = max_tokens
            settings.temperature = temperature

    @staticmethod
    def _message_to_dict(message: ChatMessage) -> dict[str, str]:
        return cast(dict[str, str], {"role": message.role, "content": message.content})

    def _load_via_local_service(self) -> None:
        """Use the local OpenAI-compatible Foundry daemon when direct SDK load is unavailable."""
        model = self._manager.get_model(self.model_alias)
        model_id = str(getattr(model, "id", "")).strip()
        if not model_id:
            raise FoundryProviderError("Foundry Local chat model id is unavailable.")
        self._local_service_model_id = model_id
        self._local_service_model_owned = not self._model_was_loaded(model)
        self._run_foundry(["model", "load", model_id], timeout_seconds=180)
        base_url = self._local_service_base_url()
        from openai import OpenAI

        self._local_service_client = OpenAI(base_url=f"{base_url}/v1", api_key="local-foundry")
        self._client = None

    def _unload_local_service_model(self) -> None:
        if self._local_service_model_id is None:
            return
        self._run_foundry(
            ["model", "unload", self._local_service_model_id],
            timeout_seconds=120,
            check=False,
        )

    def _model_id(self) -> str:
        model = self._model or self._manager.get_model(self.model_alias)
        model_id = str(getattr(model, "id", "")).strip()
        if not model_id:
            raise FoundryProviderError("Foundry Local chat model id is unavailable.")
        return model_id

    def _rollback_direct_load(self) -> None:
        model = self._model
        try:
            if model is not None and self._direct_model_owned:
                model.unload()
        except Exception:
            pass
        finally:
            self._client = None
            self._model = None
            self._direct_model_owned = False

    def _rollback_local_service_load(self) -> None:
        try:
            if self._local_service_model_id is not None and self._local_service_model_owned:
                self._unload_local_service_model()
        except Exception:
            pass
        finally:
            self._clear_provider_state()

    def _clear_provider_state(self) -> None:
        self._local_service_client = None
        self._local_service_model_id = None
        self._local_service_model_owned = False
        self._client = None
        self._model = None
        self._direct_model_owned = False

    @staticmethod
    def _model_was_loaded(model: Any) -> bool:
        try:
            return bool(getattr(model, "is_loaded", False))
        except Exception:
            return True

    @classmethod
    def _local_service_base_url(cls) -> str:
        completed = cls._run_foundry(["server", "status"], timeout_seconds=30)
        match = re.search(r"http://(?:127\.0\.0\.1|localhost|\[::1\]|::1):\d+", completed.stdout)
        if match is None:
            raise FoundryProviderError("Foundry Local service URL is unavailable.")
        return match.group(0)

    @staticmethod
    def _run_foundry(
        arguments: list[str],
        *,
        timeout_seconds: int,
        check: bool = True,
    ) -> subprocess.CompletedProcess[str]:
        foundry_path = shutil.which("foundry")
        if foundry_path is None:
            raise FoundryProviderError("Foundry Local CLI is not available.")
        completed = subprocess.run(
            [foundry_path, *arguments],
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout_seconds,
        )
        if check and completed.returncode != 0:
            raise FoundryProviderError("Foundry Local CLI command failed.")
        return completed
