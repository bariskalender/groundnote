"""Lightweight SQLite migration runner."""

from __future__ import annotations

import re
import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from groundnote.storage.exceptions import MigrationError

MIGRATION_RE = re.compile(r"^(?P<version>\d{3})_(?P<name>[a-z0-9_]+)\.sql$")


@dataclass(frozen=True)
class Migration:
    version: int
    name: str
    path: Path


class MigrationRunner:
    """Apply versioned SQL migrations transactionally."""

    def __init__(self, migrations_directory: Path | None = None) -> None:
        self.migrations_directory = migrations_directory or Path(__file__).with_name("migrations")

    def apply(self, connection: sqlite3.Connection) -> list[Migration]:
        migrations = self.discover()
        self._ensure_table(connection)
        applied_versions = self._applied_versions(connection)
        applied_now: list[Migration] = []

        for migration in migrations:
            if migration.version in applied_versions:
                continue
            try:
                connection.execute("BEGIN")
                for statement in _split_sql_statements(migration.path.read_text(encoding="utf-8")):
                    connection.execute(statement)
                connection.execute(
                    """
                    INSERT INTO schema_migrations (version, name, applied_at)
                    VALUES (?, ?, ?)
                    """,
                    (migration.version, migration.name, datetime.now(UTC).isoformat()),
                )
                connection.execute("COMMIT")
                applied_now.append(migration)
            except Exception as exc:
                connection.execute("ROLLBACK")
                raise MigrationError(f"Could not apply migration {migration.version:03d}.") from exc
        return applied_now

    def discover(self) -> list[Migration]:
        if not self.migrations_directory.exists():
            raise MigrationError("Migration directory does not exist.")

        migrations: list[Migration] = []
        seen_versions: set[int] = set()
        for path in sorted(self.migrations_directory.glob("*.sql")):
            match = MIGRATION_RE.fullmatch(path.name)
            if match is None:
                raise MigrationError("Invalid migration filename.")
            version = int(match.group("version"))
            if version in seen_versions:
                raise MigrationError("Duplicate migration version.")
            seen_versions.add(version)
            migrations.append(Migration(version=version, name=match.group("name"), path=path))
        return migrations

    @staticmethod
    def _ensure_table(connection: sqlite3.Connection) -> None:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS schema_migrations (
                version INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                applied_at TEXT NOT NULL
            )
            """
        )

    @staticmethod
    def _applied_versions(connection: sqlite3.Connection) -> set[int]:
        rows = connection.execute("SELECT version FROM schema_migrations").fetchall()
        return {int(row["version"]) for row in rows}


def _split_sql_statements(sql: str) -> list[str]:
    return [statement.strip() for statement in sql.split(";") if statement.strip()]
