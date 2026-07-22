from __future__ import annotations

import os
from pathlib import Path

import pytest

from groundnote.documents import (
    ManagedFileCleanupStatus,
    remove_managed_document_copy,
)


def test_removes_unicode_filename_with_spaces_inside_managed_root(tmp_path: Path) -> None:
    managed_root = tmp_path / "managed documents"
    managed_root.mkdir()
    target = managed_root / "Türkçe çalışma notu.txt"
    target.write_text("local managed copy", encoding="utf-8")

    result = remove_managed_document_copy(
        managed_root=managed_root,
        stored_filename=target.name,
    )

    assert result.status is ManagedFileCleanupStatus.REMOVED
    assert target.exists() is False


@pytest.mark.parametrize("stored_filename", ["../outside.txt", "folder/file.txt", "..\\x.txt"])
def test_rejects_traversal_and_preserves_outside_file(
    tmp_path: Path,
    stored_filename: str,
) -> None:
    managed_root = tmp_path / "managed"
    managed_root.mkdir()
    outside = tmp_path / "outside.txt"
    outside.write_text("external original", encoding="utf-8")

    result = remove_managed_document_copy(
        managed_root=managed_root,
        stored_filename=stored_filename,
    )

    assert result.status is ManagedFileCleanupStatus.REJECTED
    assert outside.read_text(encoding="utf-8") == "external original"


def test_missing_managed_copy_is_an_idempotent_success(tmp_path: Path) -> None:
    managed_root = tmp_path / "managed"
    managed_root.mkdir()

    result = remove_managed_document_copy(
        managed_root=managed_root,
        stored_filename="already-removed.txt",
    )

    assert result.status is ManagedFileCleanupStatus.MISSING
    assert result.complete is True


def test_rejects_symlink_without_deleting_target_when_supported(tmp_path: Path) -> None:
    managed_root = tmp_path / "managed"
    managed_root.mkdir()
    outside = tmp_path / "outside.txt"
    outside.write_text("external original", encoding="utf-8")
    link = managed_root / "managed-link.txt"
    try:
        os.symlink(outside, link)
    except OSError:
        pytest.skip("File symlink creation is unavailable on this Windows account.")

    result = remove_managed_document_copy(
        managed_root=managed_root,
        stored_filename=link.name,
    )

    assert result.status is ManagedFileCleanupStatus.REJECTED
    assert link.exists()
    assert outside.read_text(encoding="utf-8") == "external original"
