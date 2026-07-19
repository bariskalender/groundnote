from __future__ import annotations

from pathlib import Path

import pytest

from groundnote.documents.errors import UnsafeFileError
from groundnote.documents.uploads import write_uploaded_bytes


def test_write_uploaded_bytes_creates_unique_file_without_overwrite(tmp_path: Path) -> None:
    first = write_uploaded_bytes(
        b"alpha",
        original_filename="notes.txt",
        target_directory=tmp_path,
    )
    second = write_uploaded_bytes(
        b"beta",
        original_filename="notes.txt",
        target_directory=tmp_path,
    )

    assert first != second
    assert first.read_bytes() == b"alpha"
    assert second.read_bytes() == b"beta"
    assert first.parent == tmp_path


def test_write_uploaded_bytes_rejects_traversal_filename(tmp_path: Path) -> None:
    with pytest.raises(UnsafeFileError):
        write_uploaded_bytes(
            b"alpha",
            original_filename="../notes.txt",
            target_directory=tmp_path,
        )
