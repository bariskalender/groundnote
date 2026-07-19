"""Thin wrapper around Microsoft Foundry Local SDK initialization and catalog access."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from groundnote.ai.errors import FoundryCatalogError, FoundryModelUnavailableError
from groundnote.ai.models import ModelInfo


class FoundryManager:
    """Initialize Foundry Local lazily and expose provider-neutral model summaries."""

    def __init__(
        self,
        *,
        app_name: str = "groundnote",
        app_data_dir: Path | None = None,
        model_cache_dir: Path | None = None,
        logs_dir: Path | None = None,
    ) -> None:
        self.app_name = app_name
        self.app_data_dir = app_data_dir
        self.model_cache_dir = model_cache_dir
        self.logs_dir = logs_dir
        self._manager: Any | None = None

    @property
    def manager(self) -> Any:
        if self._manager is None:
            self._manager = self._initialize_manager()
        return self._manager

    def list_models(self) -> list[ModelInfo]:
        try:
            return [self._to_model_info(model) for model in self.manager.catalog.list_models()]
        except Exception as exc:  # pragma: no cover - exercised by manual Foundry checks
            raise FoundryCatalogError("Could not list Foundry Local models.") from exc

    def get_model(self, alias: str) -> Any:
        try:
            return self.manager.catalog.get_model(alias)
        except Exception as exc:  # pragma: no cover - SDK-specific behavior
            raise FoundryModelUnavailableError(
                f"Foundry Local model alias is not available: {alias}"
            ) from exc

    def get_model_info(self, alias: str) -> ModelInfo:
        return self._to_model_info(self.get_model(alias))

    def download_execution_providers(self) -> None:
        callback = getattr(self.manager, "download_and_register_eps", None)
        if callable(callback):
            callback()

    def _initialize_manager(self) -> Any:
        try:
            from foundry_local_sdk import (  # type: ignore[import-untyped]
                Configuration,
                FoundryLocalManager,
            )
        except ImportError as exc:  # pragma: no cover - depends on optional SDK install
            raise FoundryCatalogError(
                "Foundry Local SDK is not installed. Run `uv sync` for this project."
            ) from exc

        try:
            config = Configuration(
                app_name=self.app_name,
                app_data_dir=self._path_to_str(self.app_data_dir),
                model_cache_dir=self._path_to_str(self.model_cache_dir),
                logs_dir=self._path_to_str(self.logs_dir),
            )
            existing = getattr(FoundryLocalManager, "instance", None)
            if existing is not None:
                return existing
            FoundryLocalManager.initialize(config)
            return FoundryLocalManager.instance
        except Exception as exc:  # pragma: no cover - SDK-specific behavior
            raise FoundryCatalogError("Could not initialize Foundry Local SDK.") from exc

    @staticmethod
    def _path_to_str(path: Path | None) -> str | None:
        return str(path) if path is not None else None

    @classmethod
    def _to_model_info(cls, model: Any) -> ModelInfo:
        variant = cls._selected_variant(model)
        model_info = getattr(variant, "_model_info", None)
        runtime = getattr(model_info, "runtime", None)

        return ModelInfo(
            alias=str(getattr(model, "alias", "")),
            model_id=str(getattr(model, "id", "")),
            task=str(getattr(model_info, "task", "")),
            device_type=str(getattr(runtime, "device_type", "")),
            execution_provider=str(getattr(runtime, "execution_provider", "")),
            file_size_mb=getattr(model_info, "file_size_mb", None),
            context_length=getattr(model, "context_length", None),
            is_cached=bool(getattr(model, "is_cached", False)),
            is_loaded=bool(getattr(model, "is_loaded", False)),
        )

    @staticmethod
    def _selected_variant(model: Any) -> Any:
        variants = getattr(model, "variants", [])
        if variants:
            return variants[0]
        return model
