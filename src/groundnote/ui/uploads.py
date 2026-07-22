"""Rerun-safe registration for one ephemeral Streamlit upload."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from typing import Any

from groundnote.ui.formatting import safe_filename
from groundnote.ui.state import LAST_UPLOAD_SELECTION_TOKEN, SessionStateLike


@dataclass(frozen=True)
class SelectedUpload:
    """Immediate single-file input; bytes are never retained in session state."""

    identity: str
    filename: str
    content_sha256: str
    data: bytes = field(repr=False)


@dataclass(frozen=True)
class UploadRegistration:
    """Result of registering one uploader selection."""

    selection: SelectedUpload | None
    blocked: bool = False


def register_selected_upload(
    state: SessionStateLike,
    uploaded_file: object | None,
    *,
    block_new: bool = False,
) -> UploadRegistration:
    """Read and hash one new selection exactly once without storing its bytes."""
    if uploaded_file is None:
        return UploadRegistration(selection=None)
    if block_new:
        return UploadRegistration(selection=None, blocked=True)

    selection_token = _selection_token(uploaded_file)
    if _get(state, LAST_UPLOAD_SELECTION_TOKEN) == selection_token:
        return UploadRegistration(selection=None)

    filename = safe_filename(str(getattr(uploaded_file, "name", "document")))
    data = read_uploaded_bytes(uploaded_file)
    content_sha256 = hashlib.sha256(data).hexdigest()
    identity = _upload_identity_from_hash(filename, len(data), content_sha256)
    state[LAST_UPLOAD_SELECTION_TOKEN] = selection_token
    return UploadRegistration(
        selection=SelectedUpload(
            identity=identity,
            filename=filename,
            content_sha256=content_sha256,
            data=data,
        )
    )


def read_uploaded_bytes(uploaded: object) -> bytes:
    """Copy selected bytes for the immediate synchronous operation only."""
    getvalue = getattr(uploaded, "getvalue", None)
    if not callable(getvalue):
        raise RuntimeError("Uploaded content is unavailable.")
    return bytes(getvalue())


def upload_identity(filename: str, data: bytes) -> str:
    """Build a stable opaque identity from safe name, size, and content hash."""
    content_hash = hashlib.sha256(data).hexdigest()
    return _upload_identity_from_hash(filename, len(data), content_hash)


def _selection_token(uploaded: object) -> str:
    """Identify the browser selection without reading or retaining document bytes."""
    file_id = getattr(uploaded, "file_id", None)
    if file_id is not None:
        return f"file:{file_id}"
    name = safe_filename(str(getattr(uploaded, "name", "document")))
    size = getattr(uploaded, "size", None)
    media_type = getattr(uploaded, "type", None)
    return f"object:{id(uploaded)}:{name}:{size}:{media_type}"


def _upload_identity_from_hash(filename: str, size: int, content_hash: str) -> str:
    material = f"{safe_filename(filename)}\0{size}\0{content_hash}".encode()
    return hashlib.sha256(material).hexdigest()


def _get(state: SessionStateLike, key: str) -> Any:
    return getattr(state, "get", lambda _key, _default=None: _default)(key, None)
