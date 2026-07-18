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
