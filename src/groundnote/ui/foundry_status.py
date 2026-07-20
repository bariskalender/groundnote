"""Lightweight, non-model Foundry Local service status checks."""

from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass
from enum import StrEnum


class FoundryStatusKind(StrEnum):
    """Small UI-facing Foundry service states."""

    READY = "ready"
    NOT_RUNNING = "not_running"
    UNAVAILABLE = "unavailable"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class FoundryStatus:
    """Safe Foundry status without CLI output or daemon URLs."""

    kind: FoundryStatusKind
    label: str
    instruction: str | None = None


class FoundryStatusService:
    """Check the fixed local CLI status command without loading a model."""

    def check(self) -> FoundryStatus:
        foundry_path = shutil.which("foundry")
        if foundry_path is None:
            return FoundryStatus(
                FoundryStatusKind.UNAVAILABLE,
                "Unavailable",
                "Install Microsoft Foundry Local, then restart GroundNote.",
            )
        try:
            completed = subprocess.run(
                [foundry_path, "server", "status"],
                check=False,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=10,
            )
        except (OSError, subprocess.SubprocessError):
            return FoundryStatus(
                FoundryStatusKind.UNKNOWN,
                "Unknown",
                "Run `foundry server status` in a terminal.",
            )
        output = f"{completed.stdout}\n{completed.stderr}".lower()
        if "not running" in output or "stopped" in output:
            return FoundryStatus(
                FoundryStatusKind.NOT_RUNNING,
                "Not running",
                "Run `foundry server start` in a terminal.",
            )
        if completed.returncode == 0 and ("ready" in output or "reachable" in output):
            return FoundryStatus(FoundryStatusKind.READY, "Ready")
        return FoundryStatus(
            FoundryStatusKind.UNKNOWN,
            "Unknown",
            "Run `foundry server status` in a terminal.",
        )
