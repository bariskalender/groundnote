"""Semantic retrieval package."""

from groundnote.retrieval.errors import EmptyQueryError, RetrievalError, SimilarityError
from groundnote.retrieval.filters import make_semantic_query
from groundnote.retrieval.models import RetrievalResponse, RetrievalResult, SemanticQuery
from groundnote.retrieval.service import SemanticRetrievalService
from groundnote.retrieval.similarity import cosine_similarity_scores

__all__ = [
    "EmptyQueryError",
    "RetrievalError",
    "RetrievalResponse",
    "RetrievalResult",
    "SemanticQuery",
    "SemanticRetrievalService",
    "SimilarityError",
    "cosine_similarity_scores",
    "make_semantic_query",
]
