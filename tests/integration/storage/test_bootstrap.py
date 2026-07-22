from __future__ import annotations

from pathlib import Path

from groundnote.bootstrap import initialize_application
from groundnote.config import Settings


def test_bootstrap_initializes_directories_and_database(tmp_path: Path) -> None:
    settings = Settings(data_directory=tmp_path / "app-data")

    dependencies = initialize_application(settings)

    assert dependencies.settings.database_path is not None
    assert dependencies.settings.database_path.exists()
    assert dependencies.unit_of_work_factory is not None


def test_bootstrap_is_idempotent_and_preserves_existing_user_data(tmp_path: Path) -> None:
    settings = Settings(data_directory=tmp_path / "GroundNote data with spaces")
    settings.initialize_directories()
    assert settings.document_directory is not None
    existing = settings.document_directory / "keep-me.txt"
    existing.write_text("existing user data", encoding="utf-8")

    initialize_application(settings)
    initialize_application(settings)

    assert existing.read_text(encoding="utf-8") == "existing user data"
