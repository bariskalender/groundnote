"""Deterministic portable release archive support."""

from __future__ import annotations

import re
import zipfile
from pathlib import Path, PurePosixPath

from groundnote import __version__

RELEASE_ROOT_FILES = {
    ".env.example",
    "CHANGELOG.md",
    "LICENSE",
    "README.md",
    "pyproject.toml",
    "uv.lock",
}
RELEASE_DIRECTORIES = {".streamlit", "docs", "src"}
RELEASE_SCRIPTS = {
    "build_release_archive.ps1",
    "doctor.ps1",
    "setup_windows.ps1",
    "start_groundnote.ps1",
    "stop_groundnote.ps1",
}
BLOCKED_PARTS = {
    ".git",
    ".local-data",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".uv-cache",
    ".uv-python",
    ".venv",
    "__pycache__",
    "build",
    "data",
    "dist",
    "htmlcov",
    "logs",
    "model-cache",
    "models",
    "tests",
    "uploads",
    "user-data",
}
BLOCKED_SUFFIXES = {
    ".db",
    ".docx",
    ".gguf",
    ".log",
    ".npy",
    ".npz",
    ".onnx",
    ".pdf",
    ".pyc",
    ".safetensors",
    ".sqlite",
    ".sqlite3",
}
VERSION_RE = re.compile(r"^\d+\.\d+\.\d+(?:[a-z0-9.+-]+)?$")


def build_release_archive(
    repository_root: Path,
    output_directory: Path,
    *,
    version: str = __version__,
) -> Path:
    """Build a sorted ZIP from an explicit release allowlist."""
    root = repository_root.resolve()
    if not VERSION_RE.fullmatch(version):
        raise ValueError("Release version is invalid.")
    if not (root / "pyproject.toml").is_file() or not (root / "src" / "groundnote").is_dir():
        raise ValueError("Repository root is not a complete GroundNote source tree.")

    output_directory.mkdir(parents=True, exist_ok=True)
    archive_path = output_directory / f"groundnote-{version}.zip"
    files = sorted(
        (path for path in root.rglob("*") if path.is_file() and _include_path(root, path)),
        key=lambda path: path.relative_to(root).as_posix(),
    )
    prefix = PurePosixPath(f"groundnote-{version}")
    with zipfile.ZipFile(
        archive_path,
        "w",
        compression=zipfile.ZIP_DEFLATED,
        compresslevel=9,
    ) as archive:
        for path in files:
            relative = PurePosixPath(path.relative_to(root).as_posix())
            info = zipfile.ZipInfo(str(prefix / relative), date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            archive.writestr(info, path.read_bytes())
    return archive_path


def archive_members(archive_path: Path) -> tuple[str, ...]:
    """Return member names for validation without extracting the archive."""
    with zipfile.ZipFile(archive_path) as archive:
        return tuple(archive.namelist())


def _include_path(root: Path, path: Path) -> bool:
    relative = path.relative_to(root)
    parts = relative.parts
    lowered_parts = {part.lower() for part in parts}
    if lowered_parts & BLOCKED_PARTS:
        return False
    if path.suffix.lower() in BLOCKED_SUFFIXES:
        return False
    if path.name == ".env" or path.name.startswith(".env.") and path.name != ".env.example":
        return False
    if len(parts) == 1:
        return path.name in RELEASE_ROOT_FILES
    if parts[0] == "scripts":
        return len(parts) == 2 and path.name in RELEASE_SCRIPTS
    return parts[0] in RELEASE_DIRECTORIES
