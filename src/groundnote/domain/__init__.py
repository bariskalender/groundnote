"""Domain package for GroundNote."""

from groundnote.domain.answers import AnswerResult, GenerationMetadata, SourceReference
from groundnote.domain.chunks import DocumentChunk
from groundnote.domain.documents import Document, DocumentStatus, SupportedFileType
from groundnote.domain.retrieval import RetrievalResult

__all__ = [
    "AnswerResult",
    "Document",
    "DocumentChunk",
    "DocumentStatus",
    "GenerationMetadata",
    "RetrievalResult",
    "SourceReference",
    "SupportedFileType",
]
