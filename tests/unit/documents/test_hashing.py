from __future__ import annotations

from pathlib import Path

import pytest

from groundnote.documents.errors import EmptyDocumentError, UnsafeFileError
from groundnote.documents.hashing import calculate_sha256


def test_same_content_produces_same_hash(tmp_path: Path) -> None:
    first = tmp_path / "notes.txt"
    second = tmp_path / "başka-ad.txt"
    first.write_bytes(b"same content")
    second.write_bytes(b"same content")

    assert calculate_sha256(first) == calculate_sha256(second)


def test_different_content_produces_different_hash(tmp_path: Path) -> None:
    first = tmp_path / "first.txt"
    second = tmp_path / "second.txt"
    first.write_bytes(b"alpha")
    second.write_bytes(b"beta")

    assert calculate_sha256(first) != calculate_sha256(second)


def test_hash_reads_in_chunks(tmp_path: Path) -> None:
    path = tmp_path / "large.txt"
    path.write_bytes(b"a" * 10_000)

    assert calculate_sha256(path, chunk_size=128) == calculate_sha256(path)


def test_empty_file_and_invalid_path_are_rejected(tmp_path: Path) -> None:
    empty = tmp_path / "empty.txt"
    empty.write_bytes(b"")

    with pytest.raises(EmptyDocumentError):
        calculate_sha256(empty)
    with pytest.raises(UnsafeFileError):
        calculate_sha256(tmp_path / "missing.txt")
