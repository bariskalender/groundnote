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
    assert settings.maximum_pdf_pages == 1_000
    assert settings.maximum_extracted_characters == 5_000_000
    assert settings.maximum_document_chunks == 10_000
    assert settings.docx_maximum_expanded_size_mb == 200
    assert settings.docx_maximum_compression_ratio == 100.0
    assert settings.docx_maximum_member_size_mb == 50
    assert settings.docx_maximum_members == 2_000
    assert settings.rag_max_output_tokens == 320
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
        ("chunk_target_characters", 0),
        ("chunk_overlap_characters", -1),
        ("embedding_batch_size", 0),
        ("embedding_batch_size", 65),
        ("maximum_pdf_pages", 0),
        ("maximum_pdf_pages", 10_001),
        ("maximum_extracted_characters", 0),
        ("maximum_extracted_characters", 50_000_001),
        ("maximum_document_chunks", 0),
        ("maximum_document_chunks", 100_001),
        ("docx_maximum_expanded_size_mb", 0),
        ("docx_maximum_expanded_size_mb", 1_025),
        ("docx_maximum_compression_ratio", 0.9),
        ("docx_maximum_compression_ratio", 1_001.0),
        ("docx_maximum_member_size_mb", 0),
        ("docx_maximum_member_size_mb", 513),
        ("docx_maximum_members", 0),
        ("docx_maximum_members", 10_001),
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


def test_release_configuration_examples_match_active_safety_defaults() -> None:
    root = Path(__file__).resolve().parents[3]
    env_example = (root / ".env.example").read_text(encoding="utf-8")
    streamlit_config = (root / ".streamlit/config.toml").read_text(encoding="utf-8")

    assert "GROUNDNOTE_MAXIMUM_UPLOAD_SIZE_MB=50" in env_example
    assert "GROUNDNOTE_MAXIMUM_PDF_PAGES=1000" in env_example
    assert "GROUNDNOTE_MAXIMUM_EXTRACTED_CHARACTERS=5000000" in env_example
    assert "GROUNDNOTE_MAXIMUM_DOCUMENT_CHUNKS=10000" in env_example
    assert "GROUNDNOTE_DOCX_MAXIMUM_EXPANDED_SIZE_MB=200" in env_example
    assert "GROUNDNOTE_DOCX_MAXIMUM_COMPRESSION_RATIO=100" in env_example
    assert "GROUNDNOTE_DOCX_MAXIMUM_MEMBER_SIZE_MB=50" in env_example
    assert "GROUNDNOTE_DOCX_MAXIMUM_MEMBERS=2000" in env_example
    assert "GROUNDNOTE_RAG_MAX_OUTPUT_TOKENS=320" in env_example
    assert "maxUploadSize = 50" in streamlit_config
    assert 'showErrorDetails = "none"' in streamlit_config
    assert "gatherUsageStats = false" in streamlit_config
