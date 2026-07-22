from __future__ import annotations

import zipfile
from pathlib import Path

from groundnote.release import archive_members, build_release_archive


def _write(path: Path, content: str = "safe") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def test_release_archive_includes_runtime_and_excludes_private_data(tmp_path: Path) -> None:
    root = tmp_path / "GroundNote release source"
    required = (
        "pyproject.toml",
        "uv.lock",
        "README.md",
        "LICENSE",
        ".env.example",
        "CHANGELOG.md",
        ".streamlit/config.toml",
        "src/groundnote/__init__.py",
        "docs/release-checklist.md",
        "scripts/setup_windows.ps1",
        "scripts/start_groundnote.ps1",
        "scripts/stop_groundnote.ps1",
        "scripts/doctor.ps1",
        "scripts/build_release_archive.ps1",
    )
    excluded = (
        ".env",
        "data/database/private.sqlite3",
        "data/documents/private.pdf",
        "data/logs/groundnote.log",
        ".pytest_cache/state",
        ".mypy_cache/state",
        ".ruff_cache/state",
        "models/model.onnx",
        "tests/private_fixture.pdf",
    )
    for relative in required + excluded:
        _write(root / relative)

    archive = build_release_archive(root, tmp_path / "output folder", version="0.9.0")
    members = archive_members(archive)

    for relative in required:
        assert f"groundnote-0.9.0/{relative}" in members
    for relative in excluded:
        assert f"groundnote-0.9.0/{relative}" not in members
    assert archive.name == "groundnote-0.9.0.zip"


def test_release_archive_is_deterministic(tmp_path: Path) -> None:
    root = tmp_path / "source"
    _write(root / "pyproject.toml")
    _write(root / "src/groundnote/__init__.py")
    first = build_release_archive(root, tmp_path / "one", version="0.9.0")
    second = build_release_archive(root, tmp_path / "two", version="0.9.0")

    assert first.read_bytes() == second.read_bytes()
    with zipfile.ZipFile(first) as archive:
        assert all(info.date_time == (1980, 1, 1, 0, 0, 0) for info in archive.infolist())


def test_windows_scripts_are_scoped_and_repository_relative() -> None:
    root = Path(__file__).resolve().parents[2]
    start_script = (root / "scripts" / "start_groundnote.ps1").read_text(encoding="utf-8")
    stop_script = (root / "scripts" / "stop_groundnote.ps1").read_text(encoding="utf-8")
    setup_script = (root / "scripts" / "setup_windows.ps1").read_text(encoding="utf-8")

    assert "$PSScriptRoot" in start_script
    assert "127.0.0.1" in start_script
    assert "groundnote-session.json" in start_script
    assert "Get-VerifiedSession" in start_script
    assert "Get-Process -Name python" not in stop_script
    assert "taskkill" not in stop_script.lower()
    assert "ConvertFrom-Json" in stop_script
    assert "$PSScriptRoot" in setup_script
    assert "& $Uv.Source sync" in setup_script
