"""Streaming SHA-256 hashing for original document bytes."""

from __future__ import annotations

import hashlib
from pathlib import Path

from groundnote.documents.errors import EmptyDocumentError, UnsafeFileError

DEFAULT_HASH_CHUNK_SIZE = 1024 * 1024


def calculate_sha256(file_path: Path, *, chunk_size: int = DEFAULT_HASH_CHUNK_SIZE) -> str:
    """Return a lowercase SHA-256 digest for original file bytes."""
    if chunk_size <= 0:
        raise ValueError("chunk_size must be positive.")
    if not file_path.exists() or not file_path.is_file():
        raise UnsafeFileError("The file is not available for hashing.")
    if file_path.stat().st_size == 0:
        raise EmptyDocumentError()

    digest = hashlib.sha256()
    with file_path.open("rb") as file:
        for chunk in iter(lambda: file.read(chunk_size), b""):
            digest.update(chunk)
    return digest.hexdigest()
