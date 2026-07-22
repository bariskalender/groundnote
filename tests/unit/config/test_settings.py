from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from groundnote.config import Settings


def test_settings_defaults_do_not_create_directories(tmp_path: Path) -> None:
    data_dir = tmp_path / "data"

    settings = Settings(data_directory=data_dir)

    assert settings.environment == "development"
    assert settings.chat_model == "phi-3.5-mini"
    assert settings.maximum_upload_files == 10
    assert settings.maximum_upload_total_size_mb == 100
    assert settings.database_path == data_dir / "database" / "groundnote.sqlite3"
    assert not data_dir.exists()


def test_settings_environment_overrides(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    database_path = tmp_path / "custom.sqlite3"
    monkeypatch.setenv("GROUNDNOTE_TOP_K", "7")
    monkeypatch.setenv("GROUNDNOTE_DATABASE_PATH", str(database_path))

    settings = Settings(_env_file=None)

    assert settings.top_k == 7
    assert settings.database_path == database_path


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("top_k", 0),
        ("similarity_threshold", 2.0),
        ("maximum_upload_size_mb", 0),
        ("maximum_upload_files", 0),
        ("maximum_upload_files", 26),
        ("maximum_upload_total_size_mb", 0),
        ("maximum_upload_total_size_mb", 501),
        ("chunk_target_characters", 0),
        ("chunk_overlap_characters", -1),
        ("maximum_output_tokens", 4096),
        ("temperature", 2.5),
        ("embedding_batch_size", 0),
        ("embedding_batch_size", 65),
    ],
)
def test_settings_reject_invalid_simple_values(field: str, value: object) -> None:
    with pytest.raises(ValidationError):
        Settings(**{field: value})


def test_settings_reject_invalid_chunk_relationships() -> None:
    with pytest.raises(ValidationError):
        Settings(chunk_target_characters=100, chunk_maximum_characters=99)
    with pytest.raises(ValidationError):
        Settings(chunk_target_characters=100, chunk_overlap_characters=100)
    with pytest.raises(ValidationError):
        Settings(chunk_target_characters=100, chunk_minimum_characters=101)


def test_settings_reject_total_upload_limit_below_per_file_limit() -> None:
    with pytest.raises(ValidationError):
        Settings(maximum_upload_size_mb=50, maximum_upload_total_size_mb=49)


def test_settings_reject_invalid_database_suffix(tmp_path: Path) -> None:
    with pytest.raises(ValidationError):
        Settings(database_path=tmp_path / "groundnote.txt")


def test_initialize_directories_is_explicit(tmp_path: Path) -> None:
    settings = Settings(data_directory=tmp_path / "groundnote")

    settings.initialize_directories()

    assert settings.document_directory is not None
    assert settings.database_directory is not None
    assert settings.log_directory is not None
    assert settings.document_directory.exists()
    assert settings.database_directory.exists()
    assert settings.log_directory.exists()
