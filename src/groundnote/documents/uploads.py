"""Safe helpers for future uploaded file bytes."""

from __future__ import annotations

from pathlib import Path

from groundnote.documents.errors import UnsafeFileError
from groundnote.documents.validation import generate_safe_stored_filename, safe_display_filename


def write_uploaded_bytes(
    data: bytes,
    *,
    original_filename: str,
    target_directory: Path,
) -> Path:
    """Write uploaded bytes into an application-controlled directory without overwriting."""
    safe_display_filename(original_filename)
    target_directory.mkdir(parents=True, exist_ok=True)
    for _ in range(5):
        stored_filename = generate_safe_stored_filename(original_filename)
        target = target_directory / stored_filename
        try:
            with target.open("xb") as file:
                file.write(data)
            return target
        except FileExistsError:
            continue
    raise UnsafeFileError("Could not create a unique stored filename.")
