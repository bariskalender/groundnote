"""Application bootstrap for GroundNote."""

from __future__ import annotations

from dataclasses import dataclass

from groundnote.config import Settings, load_settings
from groundnote.services.index_integrity import DocumentIndexIntegrityService
from groundnote.services.indexing_ownership import ActiveIndexingRegistry
from groundnote.storage import MigrationRunner, SQLiteConnectionFactory, SQLiteUnitOfWorkFactory
from groundnote.utils import configure_logging, get_logger, safe_log_info


@dataclass(frozen=True)
class ApplicationDependencies:
    """Initialized application dependencies."""

    settings: Settings
    unit_of_work_factory: SQLiteUnitOfWorkFactory
    indexing_registry: ActiveIndexingRegistry


def initialize_application(settings: Settings | None = None) -> ApplicationDependencies:
    """Initialize settings, logging, directories, and database schema explicitly."""
    resolved_settings = settings or load_settings()
    resolved_settings.initialize_directories()
    configure_logging(resolved_settings)
    logger = get_logger(__name__)

    if resolved_settings.database_path is None:
        raise RuntimeError("Database path is not configured.")

    connection_factory = SQLiteConnectionFactory(resolved_settings.database_path)
    with connection_factory.open() as connection:
        applied = MigrationRunner().apply(connection)
    unit_of_work_factory = SQLiteUnitOfWorkFactory(resolved_settings.database_path)
    indexing_registry = ActiveIndexingRegistry(resolved_settings.database_path)
    recovery = DocumentIndexIntegrityService(
        settings=resolved_settings,
        unit_of_work_factory=unit_of_work_factory,
        indexing_registry=indexing_registry,
    ).reconcile()
    safe_log_info(
        logger,
        "application_initialized",
        migrations_applied=len(applied),
        recovered_document_count=recovery.recovered_count,
    )
    return ApplicationDependencies(
        settings=resolved_settings,
        unit_of_work_factory=unit_of_work_factory,
        indexing_registry=indexing_registry,
    )
