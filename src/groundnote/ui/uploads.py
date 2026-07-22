"""Bounded, rerun-safe, in-session upload queue state."""

from __future__ import annotations

import hashlib
import time
from dataclasses import dataclass, field, replace
from enum import StrEnum
from pathlib import Path
from typing import Any

from groundnote.ui.errors import UiMessage
from groundnote.ui.formatting import safe_filename
from groundnote.ui.state import (
    ACTIVE_UPLOAD_IDENTITY,
    COMPLETED_UPLOAD_IDENTITIES,
    FAILED_UPLOAD_IDENTITIES,
    UPLOAD_ITEMS,
    UPLOAD_QUEUE,
    UPLOAD_SUBMISSION_IDENTITIES,
    UPLOAD_WIDGET_REVISION,
    SessionStateLike,
)


class UploadStatus(StrEnum):
    """Queue lifecycle states with no database-status ambiguity."""

    WAITING = "waiting"
    VALIDATING = "validating"
    PARSING = "parsing"
    CHUNKING = "chunking"
    EMBEDDING = "embedding"
    SAVING = "saving"
    VERIFYING = "verifying"
    PROCESSING = "processing"
    INDEXING = "indexing"
    READY = "ready"
    DUPLICATE = "duplicate"
    FAILED = "failed"
    INTERRUPTED = "interrupted"
    CANCELLED = "cancelled"


TERMINAL_UPLOAD_STATUSES = frozenset(
    {
        UploadStatus.READY,
        UploadStatus.DUPLICATE,
        UploadStatus.FAILED,
        UploadStatus.INTERRUPTED,
        UploadStatus.CANCELLED,
    }
)


class UploadQueueLimitError(ValueError):
    """Base class for safe selection-limit failures."""


class UploadFileCountLimitError(UploadQueueLimitError):
    """The selected submission exceeds the configured file count."""


class UploadTotalSizeLimitError(UploadQueueLimitError):
    """The selected submission exceeds the configured retained-byte budget."""


@dataclass(frozen=True)
class UploadItemState:
    """One queue item; raw bytes exist only while the item is waiting."""

    identity: str
    submission_identity: str
    filename: str
    file_type: str
    size_bytes: int
    content_sha256: str
    sequence: int
    created_at: float
    status: UploadStatus
    current_stage: str | None = None
    completed_units: int | None = None
    total_units: int | None = None
    document_id: str | None = None
    message: UiMessage | None = None
    retry_available: bool = False
    duration_ms: float | None = None
    data: bytes | None = field(default=None, repr=False, compare=False)


@dataclass(frozen=True)
class UploadRegistration:
    """Safe registration result referring to queue IDs rather than byte buffers."""

    queued: tuple[str, ...]
    submission_identity: str | None = None
    accepted_count: int = 0
    selected_bytes: int = 0
    blocked_count: int = 0


@dataclass(frozen=True)
class UploadQueueSummary:
    """One privacy-safe terminal summary for localized display and tests."""

    total_count: int
    indexed_count: int
    duplicate_count: int
    failed_count: int
    interrupted_count: int
    cancelled_count: int
    duration_ms: float
    peak_process_rss_mb: float | None = None

    @property
    def finished(self) -> bool:
        return self.total_count == (
            self.indexed_count
            + self.duplicate_count
            + self.failed_count
            + self.interrupted_count
            + self.cancelled_count
        )


def register_selected_uploads(
    state: SessionStateLike,
    uploaded_files: list[object],
    *,
    block_new: bool = False,
    maximum_file_count: int = 10,
    maximum_total_bytes: int = 100 * 1024 * 1024,
) -> UploadRegistration:
    """Register one bounded submission without duplicating buffers on ordinary reruns."""
    current_queue = tuple(waiting_upload_ids(state))
    if block_new:
        return UploadRegistration(queued=current_queue, blocked_count=len(uploaded_files))
    if not uploaded_files:
        return UploadRegistration(queued=current_queue)
    if len(uploaded_files) > maximum_file_count:
        raise UploadFileCountLimitError(
            f"Upload file count exceeds the configured limit of {maximum_file_count}."
        )

    declared_sizes = [_declared_size(uploaded) for uploaded in uploaded_files]
    if all(size is not None for size in declared_sizes):
        declared_total = sum(size or 0 for size in declared_sizes)
        if declared_total > maximum_total_bytes:
            raise UploadTotalSizeLimitError(
                f"Upload total size exceeds the configured limit of {maximum_total_bytes} bytes."
            )

    candidates: list[tuple[str, bytes, str, str]] = []
    selected_total = 0
    for uploaded in uploaded_files:
        filename = safe_filename(str(getattr(uploaded, "name", "document")))
        data = read_uploaded_bytes(uploaded)
        selected_total += len(data)
        if selected_total > maximum_total_bytes:
            raise UploadTotalSizeLimitError(
                f"Upload total size exceeds the configured limit of {maximum_total_bytes} bytes."
            )
        digest = hashlib.sha256(data).hexdigest()
        content_identity = _upload_identity_from_hash(filename, len(data), digest)
        candidates.append((filename, data, digest, content_identity))

    revision = _nonnegative_int(_get(state, UPLOAD_WIDGET_REVISION))
    submission_identity = _submission_identity(
        revision,
        [candidate[3] for candidate in candidates],
    )
    submissions = _string_list(state, UPLOAD_SUBMISSION_IDENTITIES)
    if submission_identity in submissions:
        return UploadRegistration(
            queued=current_queue,
            submission_identity=submission_identity,
        )

    retained_total = retained_upload_bytes(state)
    if retained_total + selected_total > maximum_total_bytes:
        raise UploadTotalSizeLimitError(
            f"Upload total size exceeds the configured limit of {maximum_total_bytes} bytes."
        )

    items = _item_map(state)
    queue = _string_list(state, UPLOAD_QUEUE)
    existing_content_identities = {
        _upload_identity_from_hash(item.filename, item.size_bytes, item.content_sha256)
        for item in items.values()
    }
    unique_candidates: list[tuple[str, bytes, str, str]] = []
    seen_content_identities = set(existing_content_identities)
    for candidate in candidates:
        if candidate[3] in seen_content_identities:
            continue
        seen_content_identities.add(candidate[3])
        unique_candidates.append(candidate)
    if len(current_queue) + len(unique_candidates) > maximum_file_count:
        raise UploadFileCountLimitError(
            f"Upload queue exceeds the configured limit of {maximum_file_count}."
        )
    next_sequence = max((item.sequence for item in items.values()), default=-1) + 1
    queued_ids: list[str] = []
    created_at = time.time()
    for offset, (filename, data, digest, content_identity) in enumerate(unique_candidates):
        identity = _queue_item_identity(submission_identity, offset, content_identity)
        item = UploadItemState(
            identity=identity,
            submission_identity=submission_identity,
            filename=filename,
            file_type=_file_type(filename),
            size_bytes=len(data),
            content_sha256=digest,
            sequence=next_sequence + offset,
            created_at=created_at,
            status=UploadStatus.WAITING,
            data=data,
        )
        items[identity] = item
        queue.append(identity)
        queued_ids.append(identity)

    submissions.append(submission_identity)
    state[UPLOAD_SUBMISSION_IDENTITIES] = submissions[-100:]
    state[UPLOAD_QUEUE] = queue
    state[UPLOAD_ITEMS] = items
    return UploadRegistration(
        queued=tuple(queued_ids),
        submission_identity=submission_identity,
        accepted_count=len(queued_ids),
        selected_bytes=selected_total,
    )


def get_upload_item(state: SessionStateLike, identity: str) -> UploadItemState:
    """Return one registered item without exposing the backing state dictionary."""
    return _required_item(state, identity)


def next_waiting_upload(state: SessionStateLike) -> UploadItemState | None:
    """Return the first deterministic waiting item when no item is active."""
    if _get(state, ACTIVE_UPLOAD_IDENTITY) is not None:
        return None
    items = _item_map(state)
    for identity in _string_list(state, UPLOAD_QUEUE):
        item = items.get(identity)
        if item is not None and item.status is UploadStatus.WAITING:
            return item
    return None


def start_upload(state: SessionStateLike, identity: str) -> UploadItemState:
    """Transition exactly one waiting item to active validation."""
    if _get(state, ACTIVE_UPLOAD_IDENTITY) is not None:
        raise ValueError("Another upload queue item is already active.")
    item = _required_item(state, identity)
    if item.status is not UploadStatus.WAITING:
        raise ValueError("Only a waiting upload queue item can start.")
    if item.data is None and item.document_id is None:
        raise ValueError("The waiting upload no longer has retry data.")
    updated = replace(item, status=UploadStatus.VALIDATING, current_stage="validating")
    _replace_item(state, updated)
    state[UPLOAD_QUEUE] = [
        value for value in _string_list(state, UPLOAD_QUEUE) if value != identity
    ]
    state[ACTIVE_UPLOAD_IDENTITY] = identity
    return updated


def update_upload_status(
    state: SessionStateLike,
    identity: str,
    status: UploadStatus,
    *,
    current_stage: str | None = None,
    completed_units: int | None = None,
    total_units: int | None = None,
) -> UploadItemState:
    """Update safe progress for the active item only."""
    item = _required_active_item(state, identity)
    if status in TERMINAL_UPLOAD_STATUSES or status is UploadStatus.WAITING:
        raise ValueError("Use an explicit terminal queue transition.")
    updated = replace(
        item,
        status=status,
        current_stage=current_stage or status.value,
        completed_units=completed_units,
        total_units=total_units,
    )
    _replace_item(state, updated)
    return updated


def complete_upload(
    state: SessionStateLike,
    identity: str,
    *,
    status: UploadStatus,
    document_id: str,
    duration_ms: float | None = None,
) -> UploadItemState:
    """Complete one active item and immediately release its raw bytes."""
    if status not in {UploadStatus.READY, UploadStatus.DUPLICATE}:
        raise ValueError("Upload completion requires Ready or Duplicate status.")
    item = _required_active_item(state, identity)
    updated = replace(
        item,
        status=status,
        current_stage=status.value,
        document_id=document_id,
        message=None,
        retry_available=False,
        duration_ms=duration_ms,
        data=None,
    )
    _replace_item(state, updated)
    completed = _string_set(state, COMPLETED_UPLOAD_IDENTITIES)
    failed = _string_set(state, FAILED_UPLOAD_IDENTITIES)
    completed.add(identity)
    failed.discard(identity)
    state[COMPLETED_UPLOAD_IDENTITIES] = completed
    state[FAILED_UPLOAD_IDENTITIES] = failed
    state[ACTIVE_UPLOAD_IDENTITY] = None
    return updated


def fail_upload(
    state: SessionStateLike,
    identity: str,
    *,
    message: UiMessage,
    document_id: str | None = None,
    interrupted: bool = False,
    duration_ms: float | None = None,
) -> UploadItemState:
    """Fail only the active item, release bytes, and preserve safe retry metadata."""
    item = _required_active_item(state, identity)
    status = UploadStatus.INTERRUPTED if interrupted else UploadStatus.FAILED
    updated = replace(
        item,
        status=status,
        current_stage=status.value,
        document_id=document_id,
        message=message,
        retry_available=document_id is not None,
        duration_ms=duration_ms,
        data=None,
    )
    _replace_item(state, updated)
    failed = _string_set(state, FAILED_UPLOAD_IDENTITIES)
    completed = _string_set(state, COMPLETED_UPLOAD_IDENTITIES)
    failed.add(identity)
    completed.discard(identity)
    state[FAILED_UPLOAD_IDENTITIES] = failed
    state[COMPLETED_UPLOAD_IDENTITIES] = completed
    state[ACTIVE_UPLOAD_IDENTITY] = None
    return updated


def queue_retry(state: SessionStateLike, identity: str) -> UploadItemState:
    """Queue one persisted failed/interrupted document for explicit re-index."""
    item = _required_item(state, identity)
    queue = _string_list(state, UPLOAD_QUEUE)
    if identity in queue:
        raise ValueError("This queue retry is already waiting.")
    if item.status not in {UploadStatus.FAILED, UploadStatus.INTERRUPTED}:
        raise ValueError("Only failed or interrupted queue items can be retried.")
    if not item.retry_available or item.document_id is None:
        raise ValueError("This queue item must be selected again to retry.")
    updated = replace(
        item,
        status=UploadStatus.WAITING,
        current_stage="waiting",
        message=None,
        retry_available=False,
    )
    _replace_item(state, updated)
    queue.append(identity)
    state[UPLOAD_QUEUE] = queue
    failed = _string_set(state, FAILED_UPLOAD_IDENTITIES)
    failed.discard(identity)
    state[FAILED_UPLOAD_IDENTITIES] = failed
    return updated


def cancel_waiting_upload(state: SessionStateLike, identity: str) -> UploadItemState:
    """Cancel a waiting item without touching the current active operation."""
    item = _required_item(state, identity)
    if item.status is not UploadStatus.WAITING:
        raise ValueError("Only a waiting upload queue item can be cancelled.")
    updated = replace(
        item,
        status=UploadStatus.CANCELLED,
        current_stage="cancelled",
        retry_available=False,
        data=None,
    )
    _replace_item(state, updated)
    state[UPLOAD_QUEUE] = [
        value for value in _string_list(state, UPLOAD_QUEUE) if value != identity
    ]
    return updated


def clear_finished_uploads(state: SessionStateLike) -> int:
    """Remove terminal presentation metadata while preserving rerun deduplication."""
    items = _item_map(state)
    removed = {
        identity for identity, item in items.items() if item.status in TERMINAL_UPLOAD_STATUSES
    }
    state[UPLOAD_ITEMS] = {
        identity: item for identity, item in items.items() if identity not in removed
    }
    state[UPLOAD_QUEUE] = [
        identity for identity in _string_list(state, UPLOAD_QUEUE) if identity not in removed
    ]
    completed = _string_set(state, COMPLETED_UPLOAD_IDENTITIES)
    failed = _string_set(state, FAILED_UPLOAD_IDENTITIES)
    state[COMPLETED_UPLOAD_IDENTITIES] = completed - removed
    state[FAILED_UPLOAD_IDENTITIES] = failed - removed
    return len(removed)


def upload_items(state: SessionStateLike) -> list[UploadItemState]:
    """Return queue items in deterministic selection order."""
    return sorted(_item_map(state).values(), key=lambda item: item.sequence)


def waiting_upload_ids(state: SessionStateLike) -> list[str]:
    """Return valid waiting IDs in queue order."""
    items = _item_map(state)
    return [
        identity
        for identity in _string_list(state, UPLOAD_QUEUE)
        if identity in items and items[identity].status is UploadStatus.WAITING
    ]


def retained_upload_bytes(state: SessionStateLike) -> int:
    """Return only the bounded byte count, never queued contents."""
    return sum(len(item.data) for item in _item_map(state).values() if item.data is not None)


def summarize_upload_queue(
    state: SessionStateLike,
    *,
    duration_ms: float,
    peak_process_rss_mb: float | None = None,
    identities: list[str] | None = None,
) -> UploadQueueSummary:
    """Summarize all current queue items without claiming success while work remains."""
    allowed = set(identities) if identities is not None else None
    items = [item for item in upload_items(state) if allowed is None or item.identity in allowed]
    return UploadQueueSummary(
        total_count=len(items),
        indexed_count=sum(item.status is UploadStatus.READY for item in items),
        duplicate_count=sum(item.status is UploadStatus.DUPLICATE for item in items),
        failed_count=sum(item.status is UploadStatus.FAILED for item in items),
        interrupted_count=sum(item.status is UploadStatus.INTERRUPTED for item in items),
        cancelled_count=sum(item.status is UploadStatus.CANCELLED for item in items),
        duration_ms=duration_ms,
        peak_process_rss_mb=peak_process_rss_mb,
    )


def read_uploaded_bytes(uploaded: object) -> bytes:
    """Return the uploader's immutable bytes for one bounded waiting item."""
    getvalue = getattr(uploaded, "getvalue", None)
    if not callable(getvalue):
        raise RuntimeError("Uploaded content is unavailable.")
    value = getvalue()
    if not isinstance(value, bytes):
        return bytes(value)
    return value


def upload_identity(filename: str, data: bytes) -> str:
    """Build a stable opaque content identity from safe name, size, and hash."""
    digest = hashlib.sha256(data).hexdigest()
    return _upload_identity_from_hash(filename, len(data), digest)


def _required_active_item(state: SessionStateLike, identity: str) -> UploadItemState:
    if _get(state, ACTIVE_UPLOAD_IDENTITY) != identity:
        raise ValueError("The upload queue item is not active.")
    item = _required_item(state, identity)
    if item.status in TERMINAL_UPLOAD_STATUSES:
        raise ValueError("A terminal upload queue item cannot transition again.")
    return item


def _required_item(state: SessionStateLike, identity: str) -> UploadItemState:
    item = _item_map(state).get(identity)
    if item is None:
        raise KeyError("Upload identity is not registered.")
    return item


def _replace_item(state: SessionStateLike, item: UploadItemState) -> None:
    items = _item_map(state)
    items[item.identity] = item
    state[UPLOAD_ITEMS] = items


def _item_map(state: SessionStateLike) -> dict[str, UploadItemState]:
    value = _get(state, UPLOAD_ITEMS)
    if not isinstance(value, dict):
        return {}
    return {str(key): item for key, item in value.items() if isinstance(item, UploadItemState)}


def _declared_size(uploaded: object) -> int | None:
    value = getattr(uploaded, "size", None)
    return value if isinstance(value, int) and value >= 0 else None


def _upload_identity_from_hash(filename: str, size: int, content_hash: str) -> str:
    material = f"{safe_filename(filename)}\0{size}\0{content_hash}".encode()
    return hashlib.sha256(material).hexdigest()


def _submission_identity(revision: int, content_identities: list[str]) -> str:
    joined_identities = "\0".join(content_identities)
    material = f"{revision}\0{joined_identities}".encode()
    return hashlib.sha256(material).hexdigest()


def _queue_item_identity(submission_identity: str, index: int, content_identity: str) -> str:
    material = f"{submission_identity}\0{index}\0{content_identity}".encode()
    return hashlib.sha256(material).hexdigest()


def _file_type(filename: str) -> str:
    suffix = Path(filename).suffix.lower().lstrip(".")
    return "markdown" if suffix in {"md", "markdown"} else suffix


def _nonnegative_int(value: object) -> int:
    return value if isinstance(value, int) and value >= 0 else 0


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
