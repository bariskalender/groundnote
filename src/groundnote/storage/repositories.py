"""Repository contracts and SQLite implementations."""

from __future__ import annotations

import re
import sqlite3
from collections.abc import Sequence
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


@dataclass(frozen=True)
class SearchableChunkEmbedding:
    """Indexed chunk vector with safe document citation metadata."""

    chunk: DocumentChunk
    embedding: npt.NDArray[np.float32]
    original_filename: str
    file_type: SupportedFileType


@dataclass(frozen=True)
class LexicalChunkMatch:
    """FTS lexical match for one indexed chunk."""

    chunk_id: str
    rank: float


@dataclass(frozen=True)
class DocumentIndexIntegrity:
    """Counts used to prove that one persisted document index is complete."""

    chunk_count: int
    embedded_chunk_count: int
    compatible_embedding_count: int
    fts_row_count: int
    valid_fts_row_count: int

    @property
    def is_complete(self) -> bool:
        return (
            self.chunk_count > 0
            and self.embedded_chunk_count == self.chunk_count
            and self.compatible_embedding_count == self.chunk_count
            and self.fts_row_count == self.chunk_count
            and self.valid_fts_row_count == self.chunk_count
        )


class DocumentRepository(Protocol):
    """Document persistence contract."""

    def add(self, document: Document) -> None: ...
    def get_by_id(self, document_id: str) -> Document: ...
    def get_by_sha256(self, sha256: str) -> Document | None: ...
    def list_all(self) -> list[Document]: ...
    def update(self, document: Document) -> None: ...
    def delete(self, document_id: str) -> None: ...
    def delete_all(self) -> None: ...
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
    def save_chunk_embedding(
        self,
        *,
        chunk_id: str,
        embedding: SerializedEmbedding,
        embedding_model: str,
        embedding_version: str,
        embedded_at: datetime,
    ) -> None: ...
    def save_chunk_embeddings(
        self,
        embeddings: list[tuple[str, SerializedEmbedding]],
        *,
        embedding_model: str,
        embedding_version: str,
        embedded_at: datetime,
        sync_fts: bool = True,
    ) -> None: ...
    def sync_fts_for_document(self, document_id: str) -> None: ...
    def list_searchable_embeddings(
        self,
        *,
        embedding_model: str,
        embedding_version: str,
        document_ids: list[str] | None = None,
        file_types: list[SupportedFileType] | None = None,
        page_numbers: list[int] | None = None,
        limit: int | None = None,
    ) -> list[SearchableChunkEmbedding]: ...
    def search_lexical_chunks(
        self,
        *,
        query: str,
        embedding_model: str,
        embedding_version: str,
        document_ids: list[str] | None = None,
        file_types: list[SupportedFileType] | None = None,
        page_numbers: list[int] | None = None,
        limit: int = 50,
    ) -> list[LexicalChunkMatch]: ...
    def get_chunks_by_ids(self, chunk_ids: list[str]) -> list[DocumentChunk]: ...
    def get_searchable_chunks_by_ids(
        self,
        chunk_ids: list[str],
        *,
        embedding_model: str,
        embedding_version: str,
    ) -> list[SearchableChunkEmbedding]: ...
    def vocabulary_terms(
        self,
        *,
        document_ids: list[str] | None = None,
        file_types: list[SupportedFileType] | None = None,
        limit: int = 5000,
    ) -> list[str]: ...
    def clear_embeddings_for_document(self, document_id: str) -> None: ...
    def count_indexed_chunks(self) -> int: ...
    def count_embedded_chunks_for_document(self, document_id: str) -> int: ...
    def index_integrity(
        self,
        document_id: str,
        *,
        embedding_model: str,
        embedding_dimension: int,
        embedding_version: str,
        embedding_dtype: str,
    ) -> DocumentIndexIntegrity: ...
    def delete_fts_for_document(self, document_id: str) -> None: ...
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
                    error_message, embedding_model, embedding_dimension, embedding_version,
                    chunking_version
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                    embedding_dimension = ?, embedding_version = ?, chunking_version = ?
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

    def delete_all(self) -> None:
        """Remove every GroundNote document record in the current transaction."""
        self._connection.execute("DELETE FROM documents")

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
                    character_count, token_estimate, source_start_order, source_end_order,
                    chunking_version, metadata_json, embedding, embedding_dimension,
                    embedding_dtype, embedding_model, embedding_version, embedded_at, created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [_chunk_values(chunk, embedding) for chunk, embedding in chunks],
            )
            self._upsert_fts_rows([chunk for chunk, embedding in chunks if embedding is not None])
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

    def save_chunk_embedding(
        self,
        *,
        chunk_id: str,
        embedding: SerializedEmbedding,
        embedding_model: str,
        embedding_version: str,
        embedded_at: datetime,
    ) -> None:
        self.save_chunk_embeddings(
            [(chunk_id, embedding)],
            embedding_model=embedding_model,
            embedding_version=embedding_version,
            embedded_at=embedded_at,
        )

    def save_chunk_embeddings(
        self,
        embeddings: list[tuple[str, SerializedEmbedding]],
        *,
        embedding_model: str,
        embedding_version: str,
        embedded_at: datetime,
        sync_fts: bool = True,
    ) -> None:
        if not embeddings:
            return
        try:
            cursor = self._connection.executemany(
                """
                UPDATE document_chunks
                SET embedding = ?,
                    embedding_dimension = ?,
                    embedding_dtype = ?,
                    embedding_model = ?,
                    embedding_version = ?,
                    embedded_at = ?
                WHERE id = ?
                """,
                [
                    (
                        embedding.data,
                        embedding.dimension,
                        embedding.dtype,
                        embedding_model,
                        embedding_version,
                        _datetime_to_text(embedded_at),
                        chunk_id,
                    )
                    for chunk_id, embedding in embeddings
                ],
            )
        except sqlite3.Error as exc:
            raise StorageError("Could not save chunk embeddings.") from exc
        if cursor.rowcount != len(embeddings):
            raise StorageError("Could not save every chunk embedding.")
        if sync_fts:
            self._sync_fts_rows_for_chunk_ids([chunk_id for chunk_id, _ in embeddings])

    def sync_fts_for_document(self, document_id: str) -> None:
        """Replace FTS rows for embedded chunks belonging to one document."""
        try:
            rows = self._connection.execute(
                """
                SELECT id
                FROM document_chunks
                WHERE document_id = ? AND embedding IS NOT NULL
                ORDER BY chunk_index, id
                """,
                (document_id,),
            ).fetchall()
            self.delete_fts_for_document(document_id)
            self._sync_fts_rows_for_chunk_ids([str(row["id"]) for row in rows])
        except sqlite3.Error as exc:
            raise StorageError("Could not synchronize the document search index.") from exc

    def list_searchable_embeddings(
        self,
        *,
        embedding_model: str,
        embedding_version: str,
        document_ids: list[str] | None = None,
        file_types: list[SupportedFileType] | None = None,
        page_numbers: list[int] | None = None,
        limit: int | None = None,
    ) -> list[SearchableChunkEmbedding]:
        clauses = [
            *_complete_index_clauses(),
            "c.embedding IS NOT NULL",
            "c.embedding_model = ?",
            "c.embedding_version = ?",
        ]
        parameters: list[object] = [
            DocumentStatus.INDEXED.value,
            embedding_model,
            embedding_version,
        ]
        if document_ids is not None:
            if not document_ids:
                return []
            clauses.append(f"c.document_id IN ({_placeholders(document_ids)})")
            parameters.extend(document_ids)
        if file_types is not None:
            if not file_types:
                return []
            clauses.append(f"d.file_type IN ({_placeholders(file_types)})")
            parameters.extend(file_type.value for file_type in file_types)
        if page_numbers is not None:
            if not page_numbers:
                return []
            clauses.append(f"c.page_number IN ({_placeholders(page_numbers)})")
            parameters.extend(page_numbers)
        query = f"""
            SELECT
                c.*,
                d.original_filename AS document_original_filename,
                d.file_type AS document_file_type
            FROM document_chunks c
            JOIN documents d ON d.id = c.document_id
            WHERE {" AND ".join(clauses)}
            ORDER BY c.document_id, c.chunk_index, c.id
        """
        if limit is not None:
            query += " LIMIT ?"
            parameters.append(limit)
        rows = self._connection.execute(query, tuple(parameters)).fetchall()
        return [_searchable_embedding_from_row(row) for row in rows]

    def search_lexical_chunks(
        self,
        *,
        query: str,
        embedding_model: str,
        embedding_version: str,
        document_ids: list[str] | None = None,
        file_types: list[SupportedFileType] | None = None,
        page_numbers: list[int] | None = None,
        limit: int = 50,
    ) -> list[LexicalChunkMatch]:
        if not query.strip() or limit <= 0:
            return []
        clauses = [
            "document_chunks_fts MATCH ?",
            *_complete_index_clauses(),
            "c.embedding IS NOT NULL",
            "c.embedding_model = ?",
            "c.embedding_version = ?",
        ]
        parameters: list[object] = [
            query,
            DocumentStatus.INDEXED.value,
            embedding_model,
            embedding_version,
        ]
        if document_ids is not None:
            if not document_ids:
                return []
            clauses.append(f"c.document_id IN ({_placeholders(document_ids)})")
            parameters.extend(document_ids)
        if file_types is not None:
            if not file_types:
                return []
            clauses.append(f"d.file_type IN ({_placeholders(file_types)})")
            parameters.extend(file_type.value for file_type in file_types)
        if page_numbers is not None:
            if not page_numbers:
                return []
            clauses.append(f"c.page_number IN ({_placeholders(page_numbers)})")
            parameters.extend(page_numbers)
        parameters.append(limit)
        sql = f"""
            SELECT c.id AS chunk_id, bm25(document_chunks_fts, 1.0, 2.0, 0.8) AS rank
            FROM document_chunks_fts
            JOIN document_chunks c ON c.id = document_chunks_fts.chunk_id
            JOIN documents d ON d.id = c.document_id
            WHERE {" AND ".join(clauses)}
            ORDER BY rank, c.document_id, c.chunk_index, c.id
            LIMIT ?
        """
        try:
            rows = self._connection.execute(sql, tuple(parameters)).fetchall()
        except sqlite3.OperationalError:
            return []
        return [
            LexicalChunkMatch(chunk_id=str(row["chunk_id"]), rank=float(row["rank"]))
            for row in rows
        ]

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

    def get_searchable_chunks_by_ids(
        self,
        chunk_ids: list[str],
        *,
        embedding_model: str,
        embedding_version: str,
    ) -> list[SearchableChunkEmbedding]:
        if not chunk_ids:
            return []
        placeholders = _placeholders(chunk_ids)
        query = f"""
            SELECT
                c.*,
                d.original_filename AS document_original_filename,
                d.file_type AS document_file_type
            FROM document_chunks c
            JOIN documents d ON d.id = c.document_id
            WHERE c.id IN ({placeholders})
              AND {" AND ".join(_complete_index_clauses())}
              AND c.embedding IS NOT NULL
              AND c.embedding_model = ?
              AND c.embedding_version = ?
            ORDER BY c.document_id, c.chunk_index, c.id
        """
        rows = self._connection.execute(
            query,
            (*chunk_ids, DocumentStatus.INDEXED.value, embedding_model, embedding_version),
        ).fetchall()
        return [_searchable_embedding_from_row(row) for row in rows]

    def vocabulary_terms(
        self,
        *,
        document_ids: list[str] | None = None,
        file_types: list[SupportedFileType] | None = None,
        limit: int = 5000,
    ) -> list[str]:
        clauses = list(_complete_index_clauses())
        parameters: list[object] = [DocumentStatus.INDEXED.value]
        if document_ids is not None:
            if not document_ids:
                return []
            clauses.append(f"d.id IN ({_placeholders(document_ids)})")
            parameters.extend(document_ids)
        if file_types is not None:
            if not file_types:
                return []
            clauses.append(f"d.file_type IN ({_placeholders(file_types)})")
            parameters.extend(file_type.value for file_type in file_types)
        parameters.append(limit)
        rows = self._connection.execute(
            f"""
            SELECT c.section_title, d.original_filename
            FROM document_chunks c
            JOIN documents d ON d.id = c.document_id
            WHERE {" AND ".join(clauses)}
            ORDER BY d.created_at, c.chunk_index
            LIMIT ?
            """,
            tuple(parameters),
        ).fetchall()
        terms: set[str] = set()
        for row in rows:
            for value in (row["section_title"], row["original_filename"]):
                if value is None:
                    continue
                terms.update(_tokenize_vocabulary(str(value)))
        return sorted(terms)

    def delete_for_document(self, document_id: str) -> None:
        self.delete_fts_for_document(document_id)
        self._connection.execute(
            "DELETE FROM document_chunks WHERE document_id = ?",
            (document_id,),
        )

    def delete_fts_for_document(self, document_id: str) -> None:
        self._connection.execute(
            "DELETE FROM document_chunks_fts WHERE document_id = ?",
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
        self._connection.execute("DELETE FROM document_chunks_fts")
        self._connection.execute("DELETE FROM document_chunks")

    def clear_embeddings_for_document(self, document_id: str) -> None:
        self._connection.execute(
            """
            UPDATE document_chunks
            SET embedding = NULL,
                embedding_dimension = NULL,
                embedding_dtype = NULL,
                embedding_model = NULL,
                embedding_version = NULL,
                embedded_at = NULL
            WHERE document_id = ?
            """,
            (document_id,),
        )
        self.delete_fts_for_document(document_id)

    def _upsert_fts_rows(self, chunks: list[DocumentChunk]) -> None:
        if not chunks:
            return
        document_ids = list({chunk.document_id for chunk in chunks})
        placeholders = _placeholders(document_ids)
        rows = self._connection.execute(
            f"SELECT id, original_filename FROM documents WHERE id IN ({placeholders})",
            tuple(document_ids),
        ).fetchall()
        filenames = {str(row["id"]): str(row["original_filename"]) for row in rows}
        self._connection.executemany(
            """
            INSERT OR REPLACE INTO document_chunks_fts (
                rowid, chunk_id, document_id, content, section_title, source_filename
            )
            SELECT rowid, ?, ?, ?, ?, ?
            FROM document_chunks
            WHERE id = ?
            """,
            [
                (
                    chunk.id,
                    chunk.document_id,
                    chunk.content,
                    chunk.section_title or "",
                    filenames.get(chunk.document_id, ""),
                    chunk.id,
                )
                for chunk in chunks
            ],
        )

    def _sync_fts_rows_for_chunk_ids(self, chunk_ids: list[str]) -> None:
        if not chunk_ids:
            return
        placeholders = _placeholders(chunk_ids)
        rows = self._connection.execute(
            f"""
            SELECT c.*, d.original_filename AS document_original_filename
            FROM document_chunks c
            JOIN documents d ON d.id = c.document_id
            WHERE c.id IN ({placeholders})
            """,
            tuple(chunk_ids),
        ).fetchall()
        self._upsert_fts_rows([_chunk_from_row(row) for row in rows])

    def count_indexed_chunks(self) -> int:
        return int(
            self._connection.execute(
                "SELECT COUNT(*) FROM document_chunks WHERE embedding IS NOT NULL"
            ).fetchone()[0]
        )

    def count_embedded_chunks_for_document(self, document_id: str) -> int:
        return int(
            self._connection.execute(
                """
                SELECT COUNT(*)
                FROM document_chunks
                WHERE document_id = ? AND embedding IS NOT NULL
                """,
                (document_id,),
            ).fetchone()[0]
        )

    def index_integrity(
        self,
        document_id: str,
        *,
        embedding_model: str,
        embedding_dimension: int,
        embedding_version: str,
        embedding_dtype: str,
    ) -> DocumentIndexIntegrity:
        row = self._connection.execute(
            """
            SELECT
                (SELECT COUNT(*) FROM document_chunks WHERE document_id = ?) AS chunk_count,
                (SELECT COUNT(*) FROM document_chunks
                 WHERE document_id = ? AND embedding IS NOT NULL) AS embedded_chunk_count,
                (SELECT COUNT(*) FROM document_chunks
                 WHERE document_id = ?
                   AND embedding IS NOT NULL
                   AND embedding_model = ?
                   AND embedding_dimension = ?
                   AND embedding_version = ?
                   AND embedding_dtype = ?) AS compatible_embedding_count,
                (SELECT COUNT(*) FROM document_chunks_fts
                 WHERE document_id = ?) AS fts_row_count,
                (SELECT COUNT(DISTINCT f.chunk_id)
                 FROM document_chunks_fts f
                 JOIN document_chunks c
                   ON c.id = f.chunk_id AND c.document_id = f.document_id
                 WHERE f.document_id = ?) AS valid_fts_row_count
            """,
            (
                document_id,
                document_id,
                document_id,
                embedding_model,
                embedding_dimension,
                embedding_version,
                embedding_dtype,
                document_id,
                document_id,
            ),
        ).fetchone()
        return DocumentIndexIntegrity(
            chunk_count=int(row["chunk_count"]),
            embedded_chunk_count=int(row["embedded_chunk_count"]),
            compatible_embedding_count=int(row["compatible_embedding_count"]),
            fts_row_count=int(row["fts_row_count"]),
            valid_fts_row_count=int(row["valid_fts_row_count"]),
        )


def _complete_index_clauses() -> tuple[str, ...]:
    """Return SQL predicates that exclude every partial or inconsistent document index."""
    return (
        "d.status = ?",
        "d.indexed_at IS NOT NULL",
        "d.embedding_model IS NOT NULL",
        "d.embedding_dimension IS NOT NULL",
        "d.embedding_version IS NOT NULL",
        "EXISTS (SELECT 1 FROM document_chunks dc WHERE dc.document_id = d.id)",
        """
        NOT EXISTS (
            SELECT 1
            FROM document_chunks dc
            WHERE dc.document_id = d.id
              AND (
                  dc.embedding IS NULL
                  OR dc.embedding_model != d.embedding_model
                  OR dc.embedding_dimension != d.embedding_dimension
                  OR dc.embedding_version != d.embedding_version
                  OR dc.embedding_dtype != 'float32'
              )
        )
        """,
        """
        NOT EXISTS (
            SELECT 1
            FROM document_chunks dc
            WHERE dc.document_id = d.id
              AND NOT EXISTS (
                  SELECT 1
                  FROM document_chunks_fts f
                  WHERE f.document_id = d.id AND f.chunk_id = dc.id
              )
        )
        """,
        """
        (SELECT COUNT(*) FROM document_chunks_fts f WHERE f.document_id = d.id)
        = (SELECT COUNT(*) FROM document_chunks dc WHERE dc.document_id = d.id)
        """,
    )


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
        document.embedding_version,
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
        chunk.source_start_order,
        chunk.source_end_order,
        chunk.chunking_version,
        chunk.metadata_json,
        embedding.data if embedding is not None else None,
        embedding.dimension if embedding is not None else chunk.embedding_dimension,
        embedding.dtype if embedding is not None else None,
        chunk.embedding_model,
        chunk.embedding_version,
        _optional_datetime_to_text(chunk.embedded_at),
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
        embedding_version=_optional_str(row["embedding_version"]),
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
        embedding_model=_optional_str(row["embedding_model"]),
        embedding_version=_optional_str(row["embedding_version"]),
        embedding_dtype=_optional_str(row["embedding_dtype"]),
        embedded_at=_optional_datetime_from_text(row["embedded_at"]),
        source_start_order=_optional_int(row["source_start_order"]),
        source_end_order=_optional_int(row["source_end_order"]),
        chunking_version=_optional_str(row["chunking_version"]),
        metadata_json=_optional_str(row["metadata_json"]),
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


def _searchable_embedding_from_row(row: sqlite3.Row) -> SearchableChunkEmbedding:
    stored = _stored_embedding_from_row(row)
    if stored.embedding is None:
        raise InvalidEmbeddingError("Searchable chunk is missing an embedding.")
    return SearchableChunkEmbedding(
        chunk=stored.chunk,
        embedding=stored.embedding,
        original_filename=str(row["document_original_filename"]),
        file_type=SupportedFileType(str(row["document_file_type"])),
    )


def _placeholders(values: Sequence[object]) -> str:
    return ",".join("?" for _ in values)


def _tokenize_vocabulary(text: str) -> set[str]:
    return {token.casefold() for token in re.findall(r"[\w.-]{5,}", text, flags=re.UNICODE)}


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
