"""Repository contracts and SQLite implementations."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Protocol, cast

import numpy as np
import numpy.typing as npt

from groundnote.domain.chunks import DocumentChunk
from groundnote.domain.documents import Document, DocumentStatus, SupportedFileType
from groundnote.storage.embedding_codec import deserialize_embedding
from groundnote.storage.exceptions import (
    DocumentNotFoundError,
    DuplicateDocumentError,
    InvalidEmbeddingError,
    StorageError,
)


@dataclass(frozen=True)
class SerializedEmbedding:
    """Serialized embedding data ready for SQLite persistence."""

    data: bytes
    dimension: int
    dtype: str


@dataclass(frozen=True)
class StoredChunkEmbedding:
    """Chunk and decoded embedding returned for future vector search."""

    chunk: DocumentChunk
    embedding: npt.NDArray[np.float32] | None


class DocumentRepository(Protocol):
    """Document persistence contract."""

    def add(self, document: Document) -> None: ...
    def get_by_id(self, document_id: str) -> Document: ...
    def get_by_sha256(self, sha256: str) -> Document | None: ...
    def list_all(self) -> list[Document]: ...
    def update(self, document: Document) -> None: ...
    def delete(self, document_id: str) -> None: ...
    def count(self) -> int: ...
    def count_by_status(self, status: DocumentStatus) -> int: ...


class VectorRepository(Protocol):
    """Chunk and embedding persistence contract."""

    def add_chunk(
        self,
        chunk: DocumentChunk,
        embedding: SerializedEmbedding | None = None,
    ) -> None: ...
    def add_chunks(
        self,
        chunks: list[tuple[DocumentChunk, SerializedEmbedding | None]],
    ) -> None: ...
    def list_for_document(self, document_id: str) -> list[DocumentChunk]: ...
    def list_all_embeddings(self) -> list[StoredChunkEmbedding]: ...
    def get_chunks_by_ids(self, chunk_ids: list[str]) -> list[DocumentChunk]: ...
    def delete_for_document(self, document_id: str) -> None: ...
    def count_chunks(self) -> int: ...
    def count_chunks_for_document(self, document_id: str) -> int: ...
    def clear_all_chunks(self) -> None: ...


class SQLiteDocumentRepository:
    """SQLite implementation of document persistence."""

    def __init__(self, connection: sqlite3.Connection) -> None:
        self._connection = connection

    def add(self, document: Document) -> None:
        try:
            self._connection.execute(
                """
                INSERT INTO documents (
                    id, original_filename, stored_filename, file_type, sha256,
                    file_size_bytes, page_count, status, created_at, updated_at, indexed_at,
                    error_message, embedding_model, embedding_dimension, chunking_version
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                _document_values(document),
            )
        except sqlite3.IntegrityError as exc:
            if self.get_by_sha256(document.sha256) is not None:
                message = "A document with this SHA-256 already exists."
                raise DuplicateDocumentError(message) from exc
            raise StorageError("Could not add document.") from exc
        except sqlite3.Error as exc:
            raise StorageError("Could not add document.") from exc

    def get_by_id(self, document_id: str) -> Document:
        row = self._connection.execute(
            "SELECT * FROM documents WHERE id = ?",
            (document_id,),
        ).fetchone()
        if row is None:
            raise DocumentNotFoundError("Document was not found.")
        return _document_from_row(row)

    def get_by_sha256(self, sha256: str) -> Document | None:
        row = self._connection.execute(
            "SELECT * FROM documents WHERE sha256 = ?",
            (sha256.lower(),),
        ).fetchone()
        return _document_from_row(row) if row is not None else None

    def list_all(self) -> list[Document]:
        rows = self._connection.execute(
            "SELECT * FROM documents ORDER BY created_at, id",
        ).fetchall()
        return [_document_from_row(row) for row in rows]

    def update(self, document: Document) -> None:
        try:
            cursor = self._connection.execute(
                """
                UPDATE documents
                SET original_filename = ?, stored_filename = ?, file_type = ?, sha256 = ?,
                    file_size_bytes = ?, page_count = ?, status = ?, created_at = ?,
                    updated_at = ?, indexed_at = ?, error_message = ?, embedding_model = ?,
                    embedding_dimension = ?, chunking_version = ?
                WHERE id = ?
                """,
                (*_document_values(document)[1:], document.id),
            )
        except sqlite3.IntegrityError as exc:
            raise DuplicateDocumentError("A document with this SHA-256 already exists.") from exc
        except sqlite3.Error as exc:
            raise StorageError("Could not update document.") from exc
        if cursor.rowcount == 0:
            raise DocumentNotFoundError("Document was not found.")

    def delete(self, document_id: str) -> None:
        cursor = self._connection.execute("DELETE FROM documents WHERE id = ?", (document_id,))
        if cursor.rowcount == 0:
            raise DocumentNotFoundError("Document was not found.")

    def count(self) -> int:
        return int(self._connection.execute("SELECT COUNT(*) FROM documents").fetchone()[0])

    def count_by_status(self, status: DocumentStatus) -> int:
        return int(
            self._connection.execute(
                "SELECT COUNT(*) FROM documents WHERE status = ?",
                (status.value,),
            ).fetchone()[0]
        )


class SQLiteVectorRepository:
    """SQLite implementation of chunk and vector persistence."""

    def __init__(self, connection: sqlite3.Connection) -> None:
        self._connection = connection

    def add_chunk(
        self,
        chunk: DocumentChunk,
        embedding: SerializedEmbedding | None = None,
    ) -> None:
        self.add_chunks([(chunk, embedding)])

    def add_chunks(
        self,
        chunks: list[tuple[DocumentChunk, SerializedEmbedding | None]],
    ) -> None:
        try:
            self._connection.executemany(
                """
                INSERT INTO document_chunks (
                    id, document_id, chunk_index, content, page_number, section_title,
                    character_count, token_estimate, embedding, embedding_dimension,
                    embedding_dtype, created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [_chunk_values(chunk, embedding) for chunk, embedding in chunks],
            )
        except sqlite3.Error as exc:
            raise StorageError("Could not add document chunks.") from exc

    def list_for_document(self, document_id: str) -> list[DocumentChunk]:
        rows = self._connection.execute(
            "SELECT * FROM document_chunks WHERE document_id = ? ORDER BY chunk_index",
            (document_id,),
        ).fetchall()
        return [_chunk_from_row(row) for row in rows]

    def list_all_embeddings(self) -> list[StoredChunkEmbedding]:
        rows = self._connection.execute(
            """
            SELECT * FROM document_chunks
            WHERE embedding IS NOT NULL
            ORDER BY document_id, chunk_index
            """
        ).fetchall()
        return [_stored_embedding_from_row(row) for row in rows]

    def get_chunks_by_ids(self, chunk_ids: list[str]) -> list[DocumentChunk]:
        if not chunk_ids:
            return []
        placeholders = ",".join("?" for _ in chunk_ids)
        query = (
            f"SELECT * FROM document_chunks WHERE id IN ({placeholders}) "
            "ORDER BY document_id, chunk_index"
        )
        rows = self._connection.execute(
            query,
            tuple(chunk_ids),
        ).fetchall()
        return [_chunk_from_row(row) for row in rows]

    def delete_for_document(self, document_id: str) -> None:
        self._connection.execute(
            "DELETE FROM document_chunks WHERE document_id = ?",
            (document_id,),
        )

    def count_chunks(self) -> int:
        return int(self._connection.execute("SELECT COUNT(*) FROM document_chunks").fetchone()[0])

    def count_chunks_for_document(self, document_id: str) -> int:
        return int(
            self._connection.execute(
                "SELECT COUNT(*) FROM document_chunks WHERE document_id = ?",
                (document_id,),
            ).fetchone()[0]
        )

    def clear_all_chunks(self) -> None:
        self._connection.execute("DELETE FROM document_chunks")


def _document_values(document: Document) -> tuple[object, ...]:
    return (
        document.id,
        document.original_filename,
        document.stored_filename,
        document.file_type.value,
        document.sha256,
        document.file_size_bytes,
        document.page_count,
        document.status.value,
        _datetime_to_text(document.created_at),
        _datetime_to_text(document.updated_at),
        _optional_datetime_to_text(document.indexed_at),
        document.error_message,
        document.embedding_model,
        document.embedding_dimension,
        document.chunking_version,
    )


def _chunk_values(
    chunk: DocumentChunk,
    embedding: SerializedEmbedding | None,
) -> tuple[object, ...]:
    return (
        chunk.id,
        chunk.document_id,
        chunk.chunk_index,
        chunk.content,
        chunk.page_number,
        chunk.section_title,
        chunk.character_count,
        chunk.token_estimate,
        embedding.data if embedding is not None else None,
        embedding.dimension if embedding is not None else chunk.embedding_dimension,
        embedding.dtype if embedding is not None else None,
        _datetime_to_text(chunk.created_at),
    )


def _document_from_row(row: sqlite3.Row) -> Document:
    return Document(
        id=str(row["id"]),
        original_filename=str(row["original_filename"]),
        stored_filename=str(row["stored_filename"]),
        file_type=SupportedFileType(str(row["file_type"])),
        sha256=str(row["sha256"]),
        file_size_bytes=int(row["file_size_bytes"]),
        page_count=_optional_int(row["page_count"]),
        status=DocumentStatus(str(row["status"])),
        created_at=_datetime_from_text(str(row["created_at"])),
        updated_at=_datetime_from_text(str(row["updated_at"])),
        indexed_at=_optional_datetime_from_text(row["indexed_at"]),
        error_message=_optional_str(row["error_message"]),
        embedding_model=_optional_str(row["embedding_model"]),
        embedding_dimension=_optional_int(row["embedding_dimension"]),
        chunking_version=_optional_str(row["chunking_version"]),
    )


def _chunk_from_row(row: sqlite3.Row) -> DocumentChunk:
    return DocumentChunk(
        id=str(row["id"]),
        document_id=str(row["document_id"]),
        chunk_index=int(row["chunk_index"]),
        content=str(row["content"]),
        page_number=_optional_int(row["page_number"]),
        section_title=_optional_str(row["section_title"]),
        character_count=int(row["character_count"]),
        token_estimate=_optional_int(row["token_estimate"]),
        embedding_dimension=_optional_int(row["embedding_dimension"]),
        created_at=_datetime_from_text(str(row["created_at"])),
    )


def _stored_embedding_from_row(row: sqlite3.Row) -> StoredChunkEmbedding:
    chunk = _chunk_from_row(row)
    data = row["embedding"]
    dimension = row["embedding_dimension"]
    dtype = row["embedding_dtype"]
    if data is None:
        return StoredChunkEmbedding(chunk=chunk, embedding=None)
    if dimension is None or dtype is None:
        raise InvalidEmbeddingError("Stored embedding metadata is incomplete.")
    embedding = deserialize_embedding(
        bytes(data),
        expected_dimension=int(dimension),
        expected_dtype=str(dtype),
    )
    return StoredChunkEmbedding(chunk=chunk, embedding=embedding)


def _datetime_to_text(value: datetime) -> str:
    return value.astimezone(UTC).isoformat()


def _optional_datetime_to_text(value: datetime | None) -> str | None:
    return _datetime_to_text(value) if value is not None else None


def _datetime_from_text(value: str) -> datetime:
    return datetime.fromisoformat(value).astimezone(UTC)


def _optional_datetime_from_text(value: object) -> datetime | None:
    return _datetime_from_text(str(value)) if value is not None else None


def _optional_str(value: object) -> str | None:
    return str(value) if value is not None else None


def _optional_int(value: object) -> int | None:
    if value is None:
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        return int(value)
    return int(cast(float, value))
