"""Typed application settings for GroundNote."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Literal

from platformdirs import user_data_path
from pydantic import AliasChoices, Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

Environment = Literal["development", "test", "production"]
SUPPORTED_SQLITE_SUFFIXES = {".db", ".sqlite", ".sqlite3"}


class Settings(BaseSettings):
    """GroundNote settings loaded from defaults, `.env`, and environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="GROUNDNOTE_",
        extra="ignore",
        case_sensitive=False,
        populate_by_name=True,
    )

    app_name: str = "GroundNote"
    environment: Environment = Field(default="development", validation_alias="GROUNDNOTE_ENV")
    debug: bool = False
    log_level: str = "INFO"

    data_directory: Path | None = Field(
        default=None,
        validation_alias=AliasChoices("GROUNDNOTE_DATA_DIRECTORY", "GROUNDNOTE_DATA_DIR"),
    )
    document_directory: Path | None = None
    database_directory: Path | None = None
    database_path: Path | None = None
    log_directory: Path | None = None

    chat_model: str = "phi-3.5-mini"
    fallback_chat_model: str = Field(
        default="qwen2.5-0.5b",
        validation_alias=AliasChoices(
            "GROUNDNOTE_FALLBACK_CHAT_MODEL",
            "GROUNDNOTE_CHAT_MODEL_FALLBACK",
        ),
    )
    embedding_model: str = "qwen3-embedding-0.6b"

    top_k: int = 4
    similarity_threshold: float = 0.35
    maximum_upload_size_mb: int = Field(
        default=50,
        validation_alias=AliasChoices(
            "GROUNDNOTE_MAXIMUM_UPLOAD_SIZE_MB",
            "GROUNDNOTE_MAX_UPLOAD_MB",
        ),
    )

    chunk_target_characters: int = Field(
        default=900,
        validation_alias=AliasChoices(
            "GROUNDNOTE_CHUNK_TARGET_CHARACTERS",
            "GROUNDNOTE_CHUNK_TARGET_CHARS",
        ),
    )
    chunk_maximum_characters: int = Field(
        default=1400,
        validation_alias=AliasChoices(
            "GROUNDNOTE_CHUNK_MAXIMUM_CHARACTERS",
            "GROUNDNOTE_CHUNK_MAX_CHARS",
        ),
    )
    chunk_overlap_characters: int = Field(
        default=120,
        validation_alias=AliasChoices(
            "GROUNDNOTE_CHUNK_OVERLAP_CHARACTERS",
            "GROUNDNOTE_CHUNK_OVERLAP_CHARS",
        ),
    )
    chunk_minimum_characters: int = Field(
        default=120,
        validation_alias=AliasChoices(
            "GROUNDNOTE_CHUNK_MINIMUM_CHARACTERS",
            "GROUNDNOTE_MIN_CHUNK_CHARS",
        ),
    )
    chunking_version: str = "recursive-v1"

    maximum_output_tokens: int = 512
    temperature: float = 0.2

    @model_validator(mode="after")
    def fill_default_paths(self) -> Settings:
        base = self.data_directory or user_data_path(self.app_name, appauthor=False)
        self.data_directory = Path(base)
        self.document_directory = self.document_directory or self.data_directory / "documents"
        self.database_directory = self.database_directory or self.data_directory / "database"
        self.log_directory = self.log_directory or self.data_directory / "logs"
        self.database_path = self.database_path or self.database_directory / "groundnote.sqlite3"
        return self

    @field_validator("app_name")
    @classmethod
    def app_name_must_not_be_empty(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("app_name must not be empty.")
        return value

    @field_validator("log_level")
    @classmethod
    def log_level_must_be_valid(cls, value: str) -> str:
        normalized = value.upper()
        if normalized not in logging.getLevelNamesMapping():
            raise ValueError("log_level must be a valid Python logging level.")
        return normalized

    @field_validator("top_k")
    @classmethod
    def top_k_must_be_small(cls, value: int) -> int:
        if not 1 <= value <= 10:
            raise ValueError("top_k must be between 1 and 10.")
        return value

    @field_validator("similarity_threshold")
    @classmethod
    def similarity_threshold_must_be_cosine_range(cls, value: float) -> float:
        if not -1.0 <= value <= 1.0:
            raise ValueError("similarity_threshold must be between -1.0 and 1.0.")
        return value

    @field_validator("maximum_upload_size_mb")
    @classmethod
    def upload_size_must_be_positive(cls, value: int) -> int:
        if value <= 0:
            raise ValueError("maximum_upload_size_mb must be positive.")
        return value

    @field_validator(
        "chunk_target_characters",
        "chunk_maximum_characters",
        "chunk_minimum_characters",
    )
    @classmethod
    def chunk_sizes_must_be_positive(cls, value: int) -> int:
        if value <= 0:
            raise ValueError("chunk sizes must be positive.")
        return value

    @field_validator("chunk_overlap_characters")
    @classmethod
    def chunk_overlap_must_be_non_negative(cls, value: int) -> int:
        if value < 0:
            raise ValueError("chunk_overlap_characters must be non-negative.")
        return value

    @field_validator("maximum_output_tokens")
    @classmethod
    def maximum_output_tokens_must_be_conservative(cls, value: int) -> int:
        if not 1 <= value <= 2048:
            raise ValueError("maximum_output_tokens must be between 1 and 2048.")
        return value

    @field_validator("temperature")
    @classmethod
    def temperature_must_be_valid(cls, value: float) -> float:
        if not 0.0 <= value <= 2.0:
            raise ValueError("temperature must be between 0.0 and 2.0.")
        return value

    @model_validator(mode="after")
    def validate_related_values(self) -> Settings:
        if self.chunk_maximum_characters < self.chunk_target_characters:
            raise ValueError("chunk_maximum_characters must be greater than or equal to target.")
        if self.chunk_overlap_characters >= self.chunk_target_characters:
            raise ValueError("chunk_overlap_characters must be smaller than target.")
        if self.chunk_minimum_characters > self.chunk_target_characters:
            raise ValueError("chunk_minimum_characters must be less than or equal to target.")
        if self.database_path is None:
            raise ValueError("database_path could not be resolved.")
        if self.database_path.suffix.lower() not in SUPPORTED_SQLITE_SUFFIXES:
            raise ValueError("database_path must end with .db, .sqlite, or .sqlite3.")
        return self

    def initialize_directories(self) -> None:
        """Create application directories explicitly."""
        for directory in (
            self.data_directory,
            self.document_directory,
            self.database_directory,
            self.log_directory,
        ):
            if directory is not None:
                directory.mkdir(parents=True, exist_ok=True)


def load_settings() -> Settings:
    """Load settings from the environment and optional local `.env` file."""
    return Settings()
