"""Answer domain models for future RAG output."""

from __future__ import annotations

from pydantic import BaseModel, Field

from groundnote.domain.retrieval import RetrievalResult


class SourceReference(BaseModel):
    """Human-readable source citation metadata."""

    filename: str = Field(min_length=1)
    page_number: int | None = Field(default=None, gt=0)


class GenerationMetadata(BaseModel):
    """Provider-neutral metadata for future answer generation."""

    chat_model: str = Field(min_length=1)
    embedding_model: str = Field(min_length=1)
    prompt_version: str = Field(min_length=1)
    retrieval_duration_ms: float | None = Field(default=None, ge=0)
    generation_duration_ms: float | None = Field(default=None, ge=0)


class AnswerResult(BaseModel):
    """Answer and source data returned by future RAG flows."""

    answer: str
    sources: list[SourceReference]
    retrieved_chunks: list[RetrievalResult]
    metadata: GenerationMetadata
