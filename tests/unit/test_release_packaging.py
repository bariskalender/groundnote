from __future__ import annotations

import hashlib
import zipfile
from pathlib import Path

import pytest

from groundnote.release import archive_members, build_release_archive, checksum_path_for


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
        "CONTRIBUTING.md",
        "SECURITY.md",
        ".env.example",
        "CHANGELOG.md",
        ".streamlit/config.toml",
        "src/groundnote/__init__.py",
        "docs/release-checklist.md",
        "examples/groundnote-demo-handbook.md",
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

    archive = build_release_archive(root, tmp_path / "output folder", version="1.0.0")
    members = archive_members(archive)

    for relative in required:
        assert f"groundnote-1.0.0/{relative}" in members
    for relative in excluded:
        assert f"groundnote-1.0.0/{relative}" not in members
    assert archive.name == "groundnote-1.0.0.zip"
    checksum = checksum_path_for(archive)
    expected = hashlib.sha256(archive.read_bytes()).hexdigest()
    assert checksum.read_text(encoding="ascii") == f"{expected}  {archive.name}\n"


def test_release_archive_is_deterministic(tmp_path: Path) -> None:
    root = tmp_path / "source"
    _write(root / "pyproject.toml")
    _write(root / "src/groundnote/__init__.py")
    first = build_release_archive(root, tmp_path / "one", version="1.0.0")
    second = build_release_archive(root, tmp_path / "two", version="1.0.0")

    assert first.read_bytes() == second.read_bytes()
    assert checksum_path_for(first).read_text(encoding="ascii") == checksum_path_for(
        second
    ).read_text(encoding="ascii")
    with zipfile.ZipFile(first) as archive:
        assert all(info.date_time == (1980, 1, 1, 0, 0, 0) for info in archive.infolist())


def test_release_archive_extracts_under_path_with_spaces(tmp_path: Path) -> None:
    root = tmp_path / "source with spaces"
    _write(root / "pyproject.toml")
    _write(root / "src/groundnote/__init__.py")
    archive = build_release_archive(root, tmp_path / "release output", version="1.0.0")
    extraction = tmp_path / "extracted release with spaces"

    with zipfile.ZipFile(archive) as release:
        release.extractall(extraction)

    assert (extraction / "groundnote-1.0.0/pyproject.toml").is_file()
    assert (extraction / "groundnote-1.0.0/src/groundnote/__init__.py").is_file()


def test_release_archive_never_includes_current_or_prior_release_artifacts(tmp_path: Path) -> None:
    root = tmp_path / "source"
    _write(root / "pyproject.toml")
    _write(root / "src/groundnote/__init__.py")
    _write(root / "docs/groundnote-0.8.0.zip")
    _write(root / "docs/groundnote-0.8.0.zip.sha256")

    archive = build_release_archive(root, root / "dist", version="1.0.0")
    members = archive_members(archive)

    assert all(not member.endswith((".zip", ".zip.sha256")) for member in members)
    assert archive not in members


def test_release_archive_rejects_output_inside_allowlisted_source_directory(tmp_path: Path) -> None:
    root = tmp_path / "source"
    _write(root / "pyproject.toml")
    _write(root / "src/groundnote/__init__.py")

    with pytest.raises(ValueError, match="output"):
        build_release_archive(root, root / "docs" / "release", version="1.0.0")


def test_release_archive_rejects_symlinked_allowlisted_input(tmp_path: Path) -> None:
    root = tmp_path / "source"
    outside = tmp_path / "outside.py"
    _write(root / "pyproject.toml")
    _write(root / "src/groundnote/__init__.py")
    _write(outside, "private")
    link = root / "src/groundnote/external.py"
    try:
        link.symlink_to(outside)
    except OSError:
        pytest.skip("This Windows environment does not permit symlink creation.")

    with pytest.raises(ValueError, match="link|boundary"):
        build_release_archive(root, tmp_path / "output", version="1.0.0")


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
    assert "& $Uv.Source sync --no-dev" in setup_script
    assert "run --no-dev python" in setup_script
    assert '"run", "--no-dev", "python"' in start_script
    assert "launcher will start it" in setup_script
    assert "Stop-OwnedLaunchProcess" in start_script
    assert "SessionMetadataWritten" in start_script
    assert "groundnote-session.$Token.tmp" in start_script
    assert "Invoke-WebRequest" in start_script
    assert "Get-Process -Name python" not in start_script
