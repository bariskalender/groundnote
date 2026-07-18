from __future__ import annotations

import numpy as np
import pytest

from groundnote.domain import DocumentStatus
from groundnote.storage import (
    DuplicateDocumentError,
    SerializedEmbedding,
    SQLiteConnectionFactory,
    SQLiteDocumentRepository,
    SQLiteVectorRepository,
    serialize_embedding,
)
from groundnote.storage.exceptions import DocumentNotFoundError, InvalidEmbeddingError

from .conftest import make_chunk, make_document


def test_document_repository_crud(initialized_database) -> None:  # type: ignore[no-untyped-def]
    with SQLiteConnectionFactory(initialized_database).open() as connection:
        documents = SQLiteDocumentRepository(connection)
        document = make_document()

        documents.add(document)
        loaded = documents.get_by_id(document.id)
        document.status = DocumentStatus.PARSED
        documents.update(document)

        assert loaded.id == document.id
        assert documents.get_by_sha256(document.sha256) is not None
        assert [item.id for item in documents.list_all()] == [document.id]
        assert documents.count() == 1
        assert documents.count_by_status(DocumentStatus.PARSED) == 1
        documents.delete(document.id)
        assert documents.count() == 0
        with pytest.raises(DocumentNotFoundError):
            documents.get_by_id(document.id)


def test_document_repository_rejects_duplicate_sha(initialized_database) -> None:  # type: ignore[no-untyped-def]
    with SQLiteConnectionFactory(initialized_database).open() as connection:
        documents = SQLiteDocumentRepository(connection)
        documents.add(make_document(document_id="doc-1", sha256="b" * 64))

        with pytest.raises(DuplicateDocumentError):
            documents.add(make_document(document_id="doc-2", sha256="b" * 64))


def test_vector_repository_round_trip_and_counts(initialized_database) -> None:  # type: ignore[no-untyped-def]
    data, dimension, dtype = serialize_embedding(np.array([0.1, 0.2], dtype=np.float32))
    embedding = SerializedEmbedding(data=data, dimension=dimension, dtype=dtype)

    with SQLiteConnectionFactory(initialized_database).open() as connection:
        documents = SQLiteDocumentRepository(connection)
        vectors = SQLiteVectorRepository(connection)
        documents.add(make_document())
        chunk = make_chunk()
        vectors.add_chunk(chunk, embedding)

        loaded = vectors.list_for_document("doc-1")
        embeddings = vectors.list_all_embeddings()

        assert loaded[0].id == chunk.id
        assert embeddings[0].embedding is not None
        assert np.allclose(embeddings[0].embedding, np.array([0.1, 0.2], dtype=np.float32))
        assert vectors.count_chunks() == 1
        assert vectors.count_chunks_for_document("doc-1") == 1
        assert [item.id for item in vectors.get_chunks_by_ids(["chunk-1"])] == ["chunk-1"]


def test_cascade_delete_removes_chunks(initialized_database) -> None:  # type: ignore[no-untyped-def]
    with SQLiteConnectionFactory(initialized_database).open() as connection:
        documents = SQLiteDocumentRepository(connection)
        vectors = SQLiteVectorRepository(connection)
        documents.add(make_document())
        vectors.add_chunk(make_chunk())

        documents.delete("doc-1")

        assert vectors.count_chunks() == 0


def test_vector_repository_delete_and_clear(initialized_database) -> None:  # type: ignore[no-untyped-def]
    with SQLiteConnectionFactory(initialized_database).open() as connection:
        documents = SQLiteDocumentRepository(connection)
        vectors = SQLiteVectorRepository(connection)
        documents.add(make_document())
        vectors.add_chunks(
            [
                (make_chunk("chunk-1", chunk_index=0), None),
                (make_chunk("chunk-2", chunk_index=1), None),
            ]
        )

        vectors.delete_for_document("doc-1")
        assert vectors.count_chunks() == 0

        vectors.add_chunk(make_chunk("chunk-3"))
        vectors.clear_all_chunks()
        assert vectors.count_chunks() == 0


def test_vector_repository_rejects_malformed_stored_embedding(initialized_database) -> None:  # type: ignore[no-untyped-def]
    with SQLiteConnectionFactory(initialized_database).open() as connection:
        documents = SQLiteDocumentRepository(connection)
        vectors = SQLiteVectorRepository(connection)
        documents.add(make_document())
        chunk = make_chunk()
        vectors.add_chunk(chunk)
        connection.execute(
            """
            UPDATE document_chunks
            SET embedding = ?, embedding_dimension = ?, embedding_dtype = ?
            WHERE id = ?
            """,
            (b"bad", 2, "float32", chunk.id),
        )

        with pytest.raises(InvalidEmbeddingError):
            vectors.list_all_embeddings()
