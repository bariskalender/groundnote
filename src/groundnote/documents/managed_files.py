"""Safe cleanup for document copies owned by GroundNote."""

from __future__ import annotations

import stat
from dataclasses import dataclass
from enum import StrEnum
from os import stat_result
from pathlib import Path


class ManagedFileCleanupStatus(StrEnum):
    """Sanitized outcomes for one managed-copy cleanup attempt."""

    REMOVED = "removed"
    MISSING = "missing"
    REJECTED = "rejected"
    FAILED = "failed"


@dataclass(frozen=True)
class ManagedFileCleanupResult:
    """Cleanup outcome without exposing an absolute filesystem path."""

    status: ManagedFileCleanupStatus

    @property
    def complete(self) -> bool:
        return self.status in {
            ManagedFileCleanupStatus.REMOVED,
            ManagedFileCleanupStatus.MISSING,
        }

    @property
    def warning(self) -> bool:
        return not self.complete


def remove_managed_document_copy(
    *,
    managed_root: Path,
    stored_filename: str,
) -> ManagedFileCleanupResult:
    """Remove one direct managed child without following traversal or reparse points."""
    try:
        root = managed_root.resolve(strict=True)
    except OSError:
        return ManagedFileCleanupResult(ManagedFileCleanupStatus.FAILED)

    if not _is_safe_direct_filename(stored_filename):
        return ManagedFileCleanupResult(ManagedFileCleanupStatus.REJECTED)
    candidate = root / stored_filename
    try:
        if candidate.parent.resolve(strict=True) != root:
            return ManagedFileCleanupResult(ManagedFileCleanupStatus.REJECTED)
        file_stat = candidate.lstat()
    except FileNotFoundError:
        return ManagedFileCleanupResult(ManagedFileCleanupStatus.MISSING)
    except (OSError, ValueError):
        return ManagedFileCleanupResult(ManagedFileCleanupStatus.FAILED)

    if not stat.S_ISREG(file_stat.st_mode) or _is_reparse_point(file_stat):
        return ManagedFileCleanupResult(ManagedFileCleanupStatus.REJECTED)
    try:
        resolved = candidate.resolve(strict=True)
        if resolved.parent != root:
            return ManagedFileCleanupResult(ManagedFileCleanupStatus.REJECTED)
        candidate.unlink()
    except FileNotFoundError:
        return ManagedFileCleanupResult(ManagedFileCleanupStatus.MISSING)
    except (OSError, ValueError):
        return ManagedFileCleanupResult(ManagedFileCleanupStatus.FAILED)
    return ManagedFileCleanupResult(ManagedFileCleanupStatus.REMOVED)


def _is_safe_direct_filename(stored_filename: str) -> bool:
    if not stored_filename or stored_filename in {".", ".."}:
        return False
    try:
        candidate = Path(stored_filename)
    except (OSError, ValueError):
        return False
    return (
        not candidate.is_absolute()
        and candidate.name == stored_filename
        and "/" not in stored_filename
        and "\\" not in stored_filename
    )


def _is_reparse_point(file_stat: stat_result) -> bool:
    attributes = int(getattr(file_stat, "st_file_attributes", 0))
    reparse_flag = int(getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400))
    return stat.S_ISLNK(file_stat.st_mode) or bool(attributes & reparse_flag)
