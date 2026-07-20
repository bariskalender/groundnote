"""Provider-neutral AI data models."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

import numpy as np
import numpy.typing as npt

ChatRole = Literal["system", "user", "assistant"]


@dataclass(frozen=True)
class ChatMessage:
    """A provider-neutral chat message."""

    role: ChatRole
    content: str = field(repr=False)


@dataclass(frozen=True)
class ChatResult:
    """A provider-neutral chat completion result."""

    text: str = field(repr=False)
    model_alias: str


@dataclass(frozen=True)
class ChatGenerationRequest:
    """Provider-neutral chat generation request."""

    system_prompt: str = field(repr=False)
    user_prompt: str = field(repr=False)
    temperature: float
    max_output_tokens: int
    model: str


@dataclass(frozen=True)
class ChatGenerationResult:
    """Provider-neutral chat generation result."""

    text: str = field(repr=False)
    model: str
    duration_ms: float
    input_tokens: int | None = None
    output_tokens: int | None = None
    finish_reason: str | None = None
    warnings: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class ModelInfo:
    """Small model summary that avoids leaking SDK objects outside the AI layer."""

    alias: str
    model_id: str
    task: str
    device_type: str
    execution_provider: str
    file_size_mb: int | None
    context_length: int | None
    is_cached: bool
    is_loaded: bool


@dataclass(frozen=True)
class EmbeddingBatchResult:
    """Embedding vectors returned as finite float32 arrays."""

    vectors: npt.NDArray[np.float32] = field(repr=False)
    model_alias: str
    dimension: int
