from __future__ import annotations

from pathlib import Path

import pytest

from groundnote.storage import MigrationRunner, SQLiteConnectionFactory
from groundnote.storage.exceptions import MigrationError


def test_migrations_create_tables_and_indexes(database_path: Path) -> None:
    factory = SQLiteConnectionFactory(database_path)
    with factory.open() as connection:
        applied = MigrationRunner().apply(connection)
        tables = {
            row["name"]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            ).fetchall()
        }
        indexes = {
            row["name"]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'index'"
            ).fetchall()
        }
        foreign_keys = connection.execute("PRAGMA foreign_keys").fetchone()[0]

    assert [migration.version for migration in applied] == [1]
    assert {"documents", "document_chunks", "application_metadata"} <= tables
    assert {"idx_documents_sha256", "idx_document_chunks_document_id"} <= indexes
    assert foreign_keys == 1


def test_migrations_are_idempotent(initialized_database: Path) -> None:
    factory = SQLiteConnectionFactory(initialized_database)
    with factory.open() as connection:
        applied = MigrationRunner().apply(connection)
        count = connection.execute("SELECT COUNT(*) FROM schema_migrations").fetchone()[0]

    assert applied == []
    assert count == 1


def test_invalid_migration_rolls_back(tmp_path: Path) -> None:
    migrations = tmp_path / "migrations"
    migrations.mkdir()
    (migrations / "001_bad.sql").write_text(
        "CREATE TABLE should_rollback (id TEXT PRIMARY KEY); INVALID SQL;",
        encoding="utf-8",
    )
    factory = SQLiteConnectionFactory(tmp_path / "bad.sqlite3")

    with factory.open() as connection:
        with pytest.raises(MigrationError):
            MigrationRunner(migrations).apply(connection)
        table = connection.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table' AND name = 'should_rollback'"
        ).fetchone()

    assert table is None
