"""Retrieval domain models."""

from __future__ import annotations

from pydantic import BaseModel, Field


class RetrievalResult(BaseModel):
    """A future semantic search result."""

    chunk_id: str = Field(min_length=1)
    document_id: str = Field(min_length=1)
    filename: str = Field(min_length=1)
    page_number: int | None = Field(default=None, gt=0)
    content: str = Field(repr=False)
    similarity_score: float = Field(ge=-1.0, le=1.0)
    rank: int = Field(ge=1)
