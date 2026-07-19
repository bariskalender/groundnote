from __future__ import annotations

import numpy as np

from groundnote.ai.models import ChatMessage, ChatResult, EmbeddingBatchResult
from groundnote.domain import DocumentChunk, SupportedFileType
from groundnote.domain.retrieval import RetrievalResult as DomainRetrievalResult
from groundnote.embeddings.models import EmbeddingVector
from groundnote.retrieval.models import RetrievalResult, SemanticQuery


def test_private_text_and_vectors_are_not_exposed_in_model_reprs() -> None:
    secret_text = "PRIVATE STUDY CONTENT SHOULD NOT APPEAR"
    vector = np.array([1.0, 0.0], dtype=np.float32)

    objects = [
        ChatMessage(role="user", content=secret_text),
        ChatResult(text=secret_text, model_alias="fake"),
        EmbeddingBatchResult(vectors=np.vstack([vector]), model_alias="fake", dimension=2),
        DocumentChunk(
            id="chunk-1",
            document_id="doc-1",
            chunk_index=0,
            content=secret_text,
            character_count=len(secret_text),
        ),
        DomainRetrievalResult(
            chunk_id="chunk-1",
            document_id="doc-1",
            filename="notes.txt",
            content=secret_text,
            similarity_score=0.5,
            rank=1,
        ),
        EmbeddingVector(
            values=vector,
            dimension=2,
            dtype="float32",
            model="fake",
            version="fake-v1",
        ),
        SemanticQuery(text=secret_text, top_k=1, minimum_score=0.0),
        RetrievalResult(
            document_id="doc-1",
            chunk_id="chunk-1",
            chunk_index=0,
            content=secret_text,
            score=0.5,
            page_number=None,
            section_title=None,
            source_filename="notes.txt",
            source_file_type=SupportedFileType.TXT,
            source_start_order=0,
            source_end_order=0,
        ),
    ]

    rendered = "\n".join(repr(item) for item in objects)

    assert secret_text not in rendered
    assert "[1." not in rendered
