"""Rerun-safe automatic upload registration and display state."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, replace
from enum import StrEnum
from typing import Any

from groundnote.ui.errors import UiMessage
from groundnote.ui.formatting import safe_filename
from groundnote.ui.state import (
    ACTIVE_UPLOAD_IDENTITY,
    COMPLETED_UPLOAD_IDENTITIES,
    FAILED_UPLOAD_IDENTITIES,
    UPLOAD_ITEMS,
    UPLOAD_QUEUE,
    SessionStateLike,
)


class UploadStatus(StrEnum):
    """Compact user-facing upload lifecycle states."""

    WAITING = "waiting"
    VALIDATING = "validating"
    PROCESSING = "processing"
    INDEXING = "indexing"
    READY = "ready"
    DUPLICATE = "duplicate"
    FAILED = "failed"


@dataclass(frozen=True)
class UploadItemState:
    """Safe session metadata for one selected upload."""

    identity: str
    filename: str
    status: UploadStatus
    document_id: str | None = None
    message: UiMessage | None = None


@dataclass(frozen=True)
class SelectedUpload:
    """Ephemeral reference to a Streamlit upload; never store this in session state."""

    identity: str
    filename: str
    source: object


@dataclass(frozen=True)
class UploadRegistration:
    """New queue entries and all currently selected ephemeral file references."""

    queued: tuple[SelectedUpload, ...]
    selected: dict[str, SelectedUpload]
    blocked_count: int = 0


def register_selected_uploads(
    state: SessionStateLike,
    uploaded_files: list[object],
    *,
    block_new: bool = False,
) -> UploadRegistration:
    """Queue newly selected files once without retaining their bytes in session state."""
    if block_new:
        return UploadRegistration(queued=(), selected={}, blocked_count=len(uploaded_files))
    queue = _string_list(state, UPLOAD_QUEUE)
    completed = _string_set(state, COMPLETED_UPLOAD_IDENTITIES)
    failed = _string_set(state, FAILED_UPLOAD_IDENTITIES)
    items = _item_map(state)
    active = _get(state, ACTIVE_UPLOAD_IDENTITY)
    queued: list[SelectedUpload] = []
    queued_references: set[str] = set()
    selected: dict[str, SelectedUpload] = {}
    for uploaded in uploaded_files:
        filename = safe_filename(str(getattr(uploaded, "name", "document")))
        data = read_uploaded_bytes(uploaded)
        identity = upload_identity(filename, data)
        del data
        selection = SelectedUpload(identity=identity, filename=filename, source=uploaded)
        selected[identity] = selection
        if identity in completed or identity in failed or identity == active:
            continue
        if identity in queue:
            # Recover a previously queued selection on the next idle rerun instead of
            # leaving a permanent Waiting item with no executable file reference.
            if identity not in queued_references:
                queued.append(selection)
                queued_references.add(identity)
            continue
        queue.append(identity)
        items[identity] = UploadItemState(identity, filename, UploadStatus.WAITING)
        queued.append(selection)
        queued_references.add(identity)
    state[UPLOAD_QUEUE] = queue
    state[UPLOAD_ITEMS] = items
    return UploadRegistration(queued=tuple(queued), selected=selected)


def start_upload(state: SessionStateLike, identity: str) -> UploadItemState:
    """Mark one queued file as the active validating upload."""
    item = _required_item(state, identity)
    queue = [value for value in _string_list(state, UPLOAD_QUEUE) if value != identity]
    updated = replace(item, status=UploadStatus.VALIDATING, message=None)
    items = _item_map(state)
    items[identity] = updated
    state[UPLOAD_QUEUE] = queue
    state[UPLOAD_ITEMS] = items
    state[ACTIVE_UPLOAD_IDENTITY] = identity
    return updated


def update_upload_status(
    state: SessionStateLike,
    identity: str,
    status: UploadStatus,
) -> UploadItemState:
    """Update one active upload using safe status metadata only."""
    item = _required_item(state, identity)
    updated = replace(item, status=status)
    items = _item_map(state)
    items[identity] = updated
    state[UPLOAD_ITEMS] = items
    return updated


def complete_upload(
    state: SessionStateLike,
    identity: str,
    *,
    status: UploadStatus,
    document_id: str,
) -> UploadItemState:
    """Record a Ready or Duplicate terminal state and release the active identity."""
    if status not in {UploadStatus.READY, UploadStatus.DUPLICATE}:
        raise ValueError("Upload completion requires a terminal success status.")
    item = _required_item(state, identity)
    updated = replace(item, status=status, document_id=document_id, message=None)
    completed = _string_set(state, COMPLETED_UPLOAD_IDENTITIES)
    failed = _string_set(state, FAILED_UPLOAD_IDENTITIES)
    completed.add(identity)
    failed.discard(identity)
    items = _item_map(state)
    items[identity] = updated
    state[COMPLETED_UPLOAD_IDENTITIES] = completed
    state[FAILED_UPLOAD_IDENTITIES] = failed
    state[UPLOAD_ITEMS] = items
    state[ACTIVE_UPLOAD_IDENTITY] = None
    return updated


def fail_upload(
    state: SessionStateLike,
    identity: str,
    *,
    message: UiMessage,
    document_id: str | None = None,
) -> UploadItemState:
    """Record one isolated safe failure without retaining the original exception."""
    item = _required_item(state, identity)
    updated = replace(
        item,
        status=UploadStatus.FAILED,
        document_id=document_id,
        message=message,
    )
    failed = _string_set(state, FAILED_UPLOAD_IDENTITIES)
    completed = _string_set(state, COMPLETED_UPLOAD_IDENTITIES)
    failed.add(identity)
    completed.discard(identity)
    items = _item_map(state)
    items[identity] = updated
    state[FAILED_UPLOAD_IDENTITIES] = failed
    state[COMPLETED_UPLOAD_IDENTITIES] = completed
    state[UPLOAD_ITEMS] = items
    state[ACTIVE_UPLOAD_IDENTITY] = None
    return updated


def queue_retry(state: SessionStateLike, identity: str) -> UploadItemState:
    """Return one failed upload to Waiting for an explicit inline retry."""
    item = _required_item(state, identity)
    if item.status != UploadStatus.FAILED:
        raise ValueError("Only failed uploads can be retried.")
    queue = _string_list(state, UPLOAD_QUEUE)
    if identity not in queue:
        queue.append(identity)
    failed = _string_set(state, FAILED_UPLOAD_IDENTITIES)
    completed = _string_set(state, COMPLETED_UPLOAD_IDENTITIES)
    failed.discard(identity)
    completed.discard(identity)
    updated = replace(item, status=UploadStatus.WAITING, message=None)
    items = _item_map(state)
    items[identity] = updated
    state[UPLOAD_QUEUE] = queue
    state[FAILED_UPLOAD_IDENTITIES] = failed
    state[COMPLETED_UPLOAD_IDENTITIES] = completed
    state[UPLOAD_ITEMS] = items
    return updated


def upload_items(state: SessionStateLike) -> list[UploadItemState]:
    """Return safe upload items in selection order."""
    return list(_item_map(state).values())


def read_uploaded_bytes(uploaded: object) -> bytes:
    """Copy selected bytes for the immediate synchronous operation only."""
    getvalue = getattr(uploaded, "getvalue", None)
    if not callable(getvalue):
        raise RuntimeError("Uploaded content is unavailable.")
    return bytes(getvalue())


def upload_identity(filename: str, data: bytes) -> str:
    """Build a stable opaque identity from safe name, size, and content hash."""
    content_hash = hashlib.sha256(data).hexdigest()
    material = f"{safe_filename(filename)}\0{len(data)}\0{content_hash}".encode()
    return hashlib.sha256(material).hexdigest()


def _required_item(state: SessionStateLike, identity: str) -> UploadItemState:
    item = _item_map(state).get(identity)
    if item is None:
        raise KeyError("Upload identity is not registered.")
    return item


def _item_map(state: SessionStateLike) -> dict[str, UploadItemState]:
    value = _get(state, UPLOAD_ITEMS)
    if not isinstance(value, dict):
        return {}
    return {str(key): item for key, item in value.items() if isinstance(item, UploadItemState)}


def _string_list(state: SessionStateLike, key: str) -> list[str]:
    value = _get(state, key)
    if not isinstance(value, list):
        return []
    return [str(item) for item in value]


def _string_set(state: SessionStateLike, key: str) -> set[str]:
    value = _get(state, key)
    if not isinstance(value, set):
        return set()
    return {str(item) for item in value}


def _get(state: SessionStateLike, key: str) -> Any:
    return getattr(state, "get", lambda _key, _default=None: _default)(key, None)
