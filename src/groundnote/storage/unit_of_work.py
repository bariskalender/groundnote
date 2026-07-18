"""SQLite Unit of Work implementation."""

from __future__ import annotations

import sqlite3
from pathlib import Path
from types import TracebackType

from groundnote.storage.connection import SQLiteConnectionFactory
from groundnote.storage.repositories import SQLiteDocumentRepository, SQLiteVectorRepository


class SQLiteUnitOfWork:
    """Coordinate repositories inside one explicit SQLite transaction."""

    def __init__(self, connection_factory: SQLiteConnectionFactory) -> None:
        self._connection_factory = connection_factory
        self._connection: sqlite3.Connection | None = None
        self.documents: SQLiteDocumentRepository | None = None
        self.vectors: SQLiteVectorRepository | None = None
        self._committed = False
        self._closed = False

    def __enter__(self) -> SQLiteUnitOfWork:
        if self._closed:
            raise RuntimeError("Unit of Work cannot be reused after close.")
        self._connection = self._connection_factory.connect()
        self._connection.execute("BEGIN")
        self.documents = SQLiteDocumentRepository(self._connection)
        self.vectors = SQLiteVectorRepository(self._connection)
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        if self._connection is None:
            return
        try:
            if exc_type is not None or not self._committed:
                self._connection.rollback()
        finally:
            self._connection.close()
            self._connection = None
            self.documents = None
            self.vectors = None
            self._closed = True

    def commit(self) -> None:
        if self._connection is None or self._closed:
            raise RuntimeError("Unit of Work is not active.")
        self._connection.commit()
        self._committed = True


class SQLiteUnitOfWorkFactory:
    """Factory for SQLite Unit of Work instances."""

    def __init__(self, database_path: Path) -> None:
        self.connection_factory = SQLiteConnectionFactory(database_path)

    def __call__(self) -> SQLiteUnitOfWork:
        return SQLiteUnitOfWork(self.connection_factory)
