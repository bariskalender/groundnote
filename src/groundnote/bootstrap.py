"""Application bootstrap for GroundNote."""

from __future__ import annotations

from dataclasses import dataclass

from groundnote.config import Settings, load_settings
from groundnote.storage import MigrationRunner, SQLiteConnectionFactory, SQLiteUnitOfWorkFactory
from groundnote.utils import configure_logging, get_logger


@dataclass(frozen=True)
class ApplicationDependencies:
    """Initialized application dependencies."""

    settings: Settings
    unit_of_work_factory: SQLiteUnitOfWorkFactory


def initialize_application(settings: Settings | None = None) -> ApplicationDependencies:
    """Initialize settings, logging, directories, and database schema explicitly."""
    resolved_settings = settings or load_settings()
    configure_logging(resolved_settings)
    logger = get_logger(__name__)
    resolved_settings.initialize_directories()

    if resolved_settings.database_path is None:
        raise RuntimeError("Database path is not configured.")

    connection_factory = SQLiteConnectionFactory(resolved_settings.database_path)
    with connection_factory.open() as connection:
        applied = MigrationRunner().apply(connection)
    logger.info("application_initialized", migrations_applied=len(applied))
    return ApplicationDependencies(
        settings=resolved_settings,
        unit_of_work_factory=SQLiteUnitOfWorkFactory(resolved_settings.database_path),
    )
