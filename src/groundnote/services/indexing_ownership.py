"""Process-local ownership for synchronous document indexing operations."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from threading import RLock
from typing import TypeVar
from uuid import uuid4

from groundnote.embeddings import IndexingError

_Result = TypeVar("_Result")
_REGISTRY_LOCK = RLock()
_ACTIVE_OPERATIONS: dict[tuple[str, str], str] = {}
_PIPELINE_OWNER = "__single_upload_pipeline__"


class IndexingOperationActiveError(IndexingError):
    """Raised when a document already has an active in-process indexing owner."""


class ActiveIndexingRegistry:
    """Coordinate indexing ownership across Streamlit sessions in one process.

    The registry is intentionally process-local. A real server restart clears it, allowing
    bootstrap reconciliation to recover persisted transient rows as interrupted work.
    """

    def __init__(self, database_path: Path) -> None:
        self._scope = str(database_path.resolve(strict=False)).casefold()

    def claim(self, document_id: str, *, pipeline_token: str | None = None) -> str:
        """Claim one document and return an opaque run token."""
        key = self._key(document_id)
        with _REGISTRY_LOCK:
            pipeline_owner = _ACTIVE_OPERATIONS.get(self._key(_PIPELINE_OWNER))
            another_document_active = any(
                scope == self._scope and active_document_id != _PIPELINE_OWNER
                for scope, active_document_id in _ACTIVE_OPERATIONS
            )
            if (
                key in _ACTIVE_OPERATIONS
                or another_document_active
                or (pipeline_owner is not None and pipeline_owner != pipeline_token)
            ):
                raise IndexingOperationActiveError(
                    "GroundNote already has an active indexing operation."
                )
            token = str(uuid4())
            _ACTIVE_OPERATIONS[key] = token
            return token

    def claim_pipeline(self) -> str:
        """Own the single upload pipeline before document persistence begins."""
        key = self._key(_PIPELINE_OWNER)
        with _REGISTRY_LOCK:
            if any(scope == self._scope for scope, _identifier in _ACTIVE_OPERATIONS):
                raise IndexingOperationActiveError(
                    "GroundNote already has an active indexing operation."
                )
            token = str(uuid4())
            _ACTIVE_OPERATIONS[key] = token
            return token

    def release_pipeline(self, token: str) -> None:
        """Release the single upload pipeline owner after its terminal outcome."""
        self.release(_PIPELINE_OWNER, token)

    def pipeline_is_active(self) -> bool:
        """Return whether validation, parsing, chunking, or indexing is active."""
        return self.is_active(_PIPELINE_OWNER)

    def complete(
        self,
        document_id: str,
        token: str,
        callback: Callable[[], _Result],
    ) -> _Result:
        """Commit final index state before releasing ownership atomically to readers."""
        key = self._key(document_id)
        with _REGISTRY_LOCK:
            self._require_owner(key, token)
            result = callback()
            _ACTIVE_OPERATIONS.pop(key, None)
            return result

    def fail(
        self,
        document_id: str,
        token: str,
        callback: Callable[[], None],
    ) -> None:
        """Persist a retryable failure and then release ownership."""
        key = self._key(document_id)
        with _REGISTRY_LOCK:
            self._require_owner(key, token)
            try:
                callback()
            finally:
                _ACTIVE_OPERATIONS.pop(key, None)

    def release(self, document_id: str, token: str) -> None:
        """Release an unprepared or already-finalized claim without changing storage."""
        key = self._key(document_id)
        with _REGISTRY_LOCK:
            if _ACTIVE_OPERATIONS.get(key) == token:
                _ACTIVE_OPERATIONS.pop(key, None)

    def is_active(self, document_id: str | None = None) -> bool:
        """Return whether this database, or one document in it, is actively indexing."""
        with _REGISTRY_LOCK:
            if document_id is not None:
                return self._key(document_id) in _ACTIVE_OPERATIONS
            return any(scope == self._scope for scope, _document_id in _ACTIVE_OPERATIONS)

    def active_document_ids(self) -> frozenset[str]:
        """Return a stable snapshot for conservative UI and recovery decisions."""
        with _REGISTRY_LOCK:
            return frozenset(
                document_id
                for scope, document_id in _ACTIVE_OPERATIONS
                if scope == self._scope and document_id != _PIPELINE_OWNER
            )

    def _key(self, document_id: str) -> tuple[str, str]:
        return self._scope, document_id

    @staticmethod
    def _require_owner(key: tuple[str, str], token: str) -> None:
        if _ACTIVE_OPERATIONS.get(key) != token:
            raise IndexingOperationActiveError("Indexing ownership is no longer valid.")
