"""Privacy-safe environment diagnostics that never load or download models."""

from __future__ import annotations

import json
import os
import platform
import shutil
import socket
import sqlite3
import subprocess
from collections.abc import Callable
from dataclasses import dataclass
from enum import StrEnum
from importlib import import_module, util
from pathlib import Path
from typing import Any

from groundnote import __version__
from groundnote.config import Settings, load_settings

DEFAULT_PORT = 8501
REQUIRED_PACKAGES = (
    "streamlit",
    "pydantic",
    "pydantic_settings",
    "numpy",
    "structlog",
    "platformdirs",
    "pypdf",
    "dotenv",
    "foundry_local_sdk",
    "openai",
    "psutil",
)


class CheckLevel(StrEnum):
    """Human-facing doctor result levels."""

    OK = "OK"
    WARNING = "Warning"
    ERROR = "Error"


@dataclass(frozen=True)
class CommandResult:
    """Sanitized subprocess outcome used by the diagnostic checks."""

    returncode: int
    stdout: str = ""
    stderr: str = ""


@dataclass(frozen=True)
class DiagnosticCheck:
    """One actionable diagnostic result without private values."""

    name: str
    level: CheckLevel
    message: str


@dataclass(frozen=True)
class DoctorReport:
    """Complete local readiness report."""

    checks: tuple[DiagnosticCheck, ...]

    @property
    def ready(self) -> bool:
        return all(check.level is not CheckLevel.ERROR for check in self.checks)

    @property
    def exit_code(self) -> int:
        return 0 if self.ready else 1

    def render(self) -> str:
        lines = [f"GroundNote {__version__} environment doctor"]
        lines.extend(f"[{check.level}] {check.name}: {check.message}" for check in self.checks)
        lines.append("Result: ready" if self.ready else "Result: action required")
        return "\n".join(lines)


CommandRunner = Callable[[list[str]], CommandResult]
ExecutableFinder = Callable[[str], str | None]


def run_doctor(
    *,
    settings: Settings | None = None,
    repository_root: Path | None = None,
    port: int = DEFAULT_PORT,
    command_runner: CommandRunner | None = None,
    executable_finder: ExecutableFinder | None = None,
    operating_system: str | None = None,
    python_version: tuple[int, int, int] | None = None,
) -> DoctorReport:
    """Inspect readiness without creating directories, databases, or loading models."""
    runner = command_runner or _run_command
    find_executable = executable_finder or shutil.which
    root = (repository_root or Path(__file__).resolve().parents[2]).resolve()
    checks: list[DiagnosticCheck] = []

    system = operating_system or platform.system()
    if system in {"Windows", "Darwin"}:
        checks.append(DiagnosticCheck("Operating system", CheckLevel.OK, system))
    else:
        checks.append(
            DiagnosticCheck(
                "Operating system",
                CheckLevel.WARNING,
                f"{system} is not a primary GroundNote desktop target.",
            )
        )

    version_info = python_version or (
        int(platform.python_version_tuple()[0]),
        int(platform.python_version_tuple()[1]),
        int(platform.python_version_tuple()[2]),
    )
    version_text = ".".join(str(part) for part in version_info)
    checks.append(
        DiagnosticCheck(
            "Python",
            CheckLevel.OK if version_info[:2] == (3, 11) else CheckLevel.ERROR,
            version_text
            if version_info[:2] == (3, 11)
            else f"{version_text}; Python 3.11 is required.",
        )
    )

    uv_path = find_executable("uv")
    if uv_path is None:
        checks.append(
            DiagnosticCheck(
                "uv",
                CheckLevel.ERROR,
                "Not available. Install uv, then run scripts/setup_windows.ps1 again.",
            )
        )
    else:
        uv_result = runner([uv_path, "--version"])
        checks.append(
            DiagnosticCheck(
                "uv",
                CheckLevel.OK if uv_result.returncode == 0 else CheckLevel.ERROR,
                _first_safe_line(uv_result.stdout) or "Installed but not executable.",
            )
        )

    repository_valid = (root / "pyproject.toml").is_file() and (
        root / "src" / "groundnote"
    ).is_dir()
    checks.append(
        DiagnosticCheck(
            "Repository",
            CheckLevel.OK if repository_valid else CheckLevel.ERROR,
            f"Detected project folder '{root.name}'."
            if repository_valid
            else "Run the command from a complete GroundNote release folder.",
        )
    )

    missing_packages = [name for name in REQUIRED_PACKAGES if not _module_available(name)]
    checks.append(
        DiagnosticCheck(
            "Dependencies",
            CheckLevel.OK if not missing_packages else CheckLevel.ERROR,
            "Required Python packages are importable."
            if not missing_packages
            else "Missing packages: " + ", ".join(missing_packages) + ". Run `uv sync`.",
        )
    )

    try:
        resolved_settings = settings or load_settings()
    except Exception:
        checks.append(
            DiagnosticCheck(
                "Configuration",
                CheckLevel.ERROR,
                "Configuration is invalid. Review .env.example and local environment values.",
            )
        )
        resolved_settings = None
    else:
        assert resolved_settings is not None
        checks.append(
            DiagnosticCheck("Configuration", CheckLevel.OK, "Configuration values are valid.")
        )
        checks.extend(_path_checks(resolved_settings))
        checks.append(_database_check(resolved_settings))

    foundry_path = find_executable("foundry")
    if foundry_path is None:
        checks.append(
            DiagnosticCheck(
                "Foundry Local CLI",
                CheckLevel.ERROR,
                "Not available. Install Microsoft Foundry Local before starting GroundNote.",
            )
        )
    else:
        checks.extend(_foundry_checks(foundry_path, resolved_settings, runner))

    checks.append(_port_check(port))

    try:
        import_module("groundnote.app")
    except Exception:
        checks.append(
            DiagnosticCheck(
                "Application import",
                CheckLevel.ERROR,
                "GroundNote could not be imported. Run `uv sync` and retry.",
            )
        )
    else:
        checks.append(
            DiagnosticCheck("Application import", CheckLevel.OK, "GroundNote imports successfully.")
        )

    checks.append(_git_check(root, runner, find_executable))
    return DoctorReport(tuple(checks))


def _path_checks(settings: Settings) -> list[DiagnosticCheck]:
    paths = (
        ("Data directory", settings.data_directory),
        ("Document directory", settings.document_directory),
        ("Database directory", settings.database_directory),
        ("Log directory", settings.log_directory),
    )
    checks: list[DiagnosticCheck] = []
    for label, path in paths:
        if path is None:
            checks.append(DiagnosticCheck(label, CheckLevel.ERROR, "Path is not configured."))
        elif path.exists() and path.is_dir() and os.access(path, os.W_OK):
            checks.append(DiagnosticCheck(label, CheckLevel.OK, "Exists and is writable."))
        elif path.exists():
            checks.append(DiagnosticCheck(label, CheckLevel.ERROR, "Exists but is not writable."))
        elif _nearest_existing_directory_is_writable(path):
            checks.append(
                DiagnosticCheck(
                    label,
                    CheckLevel.WARNING,
                    "Missing; setup or first launch can create it safely.",
                )
            )
        else:
            checks.append(
                DiagnosticCheck(label, CheckLevel.ERROR, "Missing and cannot be created safely.")
            )
    return checks


def _database_check(settings: Settings) -> DiagnosticCheck:
    database_path = settings.database_path
    if database_path is None:
        return DiagnosticCheck(
            "SQLite database", CheckLevel.ERROR, "Database path is not configured."
        )
    if not database_path.exists():
        return DiagnosticCheck(
            "SQLite database",
            CheckLevel.WARNING,
            "Not created yet; setup or first launch will initialize it.",
        )
    try:
        uri = f"{database_path.resolve().as_uri()}?mode=ro"
        with sqlite3.connect(uri, uri=True) as connection:
            connection.execute("PRAGMA schema_version").fetchone()
    except sqlite3.Error:
        return DiagnosticCheck(
            "SQLite database", CheckLevel.ERROR, "Existing local database is not accessible."
        )
    return DiagnosticCheck("SQLite database", CheckLevel.OK, "Existing database is accessible.")


def _foundry_checks(
    foundry_path: str,
    settings: Settings | None,
    runner: CommandRunner,
) -> list[DiagnosticCheck]:
    checks: list[DiagnosticCheck] = []
    version_result = runner([foundry_path, "--version"])
    checks.append(
        DiagnosticCheck(
            "Foundry Local CLI",
            CheckLevel.OK if version_result.returncode == 0 else CheckLevel.ERROR,
            _first_safe_line(version_result.stdout) or "Installed but not executable.",
        )
    )

    server_result = runner([foundry_path, "server", "status", "-o", "json"])
    server_data = _json_object(server_result.stdout)
    service_state = str(server_data.get("state", "unknown")).casefold().replace("-", "_")
    running = server_data.get("running") is True
    ready = running and service_state in {"ready", "reachable"}
    stopped = not running and service_state in {"not_running", "stopped"}
    starting = service_state in {"starting", "initializing"}
    if ready:
        service_check = DiagnosticCheck("Foundry service", CheckLevel.OK, "Ready.")
    elif stopped:
        service_check = DiagnosticCheck(
            "Foundry service",
            CheckLevel.WARNING,
            "Installed but stopped. The GroundNote launcher will start it when needed.",
        )
    elif starting:
        service_check = DiagnosticCheck(
            "Foundry service",
            CheckLevel.WARNING,
            "Starting; retry readiness checks shortly.",
        )
    elif service_state in {"error", "failed", "unavailable", "unhealthy"}:
        service_check = DiagnosticCheck(
            "Foundry service",
            CheckLevel.ERROR,
            "Installed, but the local service is unavailable or unhealthy.",
        )
    elif server_result.returncode != 0 or not server_data:
        service_check = DiagnosticCheck(
            "Foundry service",
            CheckLevel.ERROR,
            "Service readiness could not be inspected.",
        )
    else:
        service_check = DiagnosticCheck(
            "Foundry service",
            CheckLevel.WARNING,
            "Installed, but service readiness is unknown.",
        )
    checks.append(service_check)

    if not ready:
        checks.append(
            DiagnosticCheck(
                "Loaded models",
                CheckLevel.WARNING,
                "Not inspected while the Foundry service is not ready.",
            )
        )
        checks.append(
            DiagnosticCheck(
                "Required models",
                CheckLevel.WARNING,
                "Not inspected while the Foundry service is not ready; no model was loaded.",
            )
        )
        return checks

    status_result = runner([foundry_path, "status", "-o", "json"])
    status_data = _json_object(status_result.stdout)
    models_data = status_data.get("models", {})
    loaded_count = _safe_int(models_data.get("loaded")) if isinstance(models_data, dict) else 0
    checks.append(
        DiagnosticCheck("Loaded models", CheckLevel.OK, f"{loaded_count} model(s) loaded.")
    )

    cache_result = runner([foundry_path, "cache", "list", "-o", "json"])
    cache_data = _json_object(cache_result.stdout)
    cached_entries = cache_data.get("models", [])
    aliases = {
        str(entry.get("alias"))
        for entry in cached_entries
        if isinstance(entry, dict) and entry.get("cached") is True
    }
    required = {settings.chat_model, settings.embedding_model} if settings is not None else set()
    fallback = settings.fast_chat_model if settings is not None else None
    missing = sorted(required - aliases)
    if cache_result.returncode != 0:
        checks.append(
            DiagnosticCheck(
                "Required models",
                CheckLevel.WARNING,
                "The local model cache could not be inspected; no model was downloaded.",
            )
        )
    elif missing:
        checks.append(
            DiagnosticCheck(
                "Required models",
                CheckLevel.WARNING,
                "Missing cached model aliases: " + ", ".join(missing) + ".",
            )
        )
    else:
        message = "Required chat and embedding models are cached."
        level = CheckLevel.OK
        if fallback and fallback not in aliases:
            message += f" Optional fallback '{fallback}' is not cached."
            level = CheckLevel.WARNING
        checks.append(DiagnosticCheck("Required models", level, message))
    return checks


def _port_check(port: int) -> DiagnosticCheck:
    if not 1 <= port <= 65535:
        return DiagnosticCheck(
            "Streamlit port", CheckLevel.ERROR, "Port must be between 1 and 65535."
        )
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
            probe.bind(("127.0.0.1", port))
    except OSError:
        return DiagnosticCheck(
            "Streamlit port",
            CheckLevel.ERROR,
            f"Local port {port} is already occupied.",
        )
    return DiagnosticCheck("Streamlit port", CheckLevel.OK, f"Local port {port} is available.")


def _git_check(
    root: Path,
    runner: CommandRunner,
    find_executable: ExecutableFinder,
) -> DiagnosticCheck:
    git_path = find_executable("git")
    if git_path is None or not (root / ".git").exists():
        return DiagnosticCheck(
            "Git checkout",
            CheckLevel.WARNING,
            "Not a Git checkout; release archives can still run.",
        )
    result = runner([git_path, "-C", str(root), "status", "--porcelain"])
    if result.returncode != 0:
        return DiagnosticCheck("Git checkout", CheckLevel.WARNING, "Git status is unavailable.")
    if result.stdout.strip():
        return DiagnosticCheck(
            "Git checkout", CheckLevel.WARNING, "Working tree has local changes."
        )
    return DiagnosticCheck("Git checkout", CheckLevel.OK, "Working tree is clean.")


def _run_command(command: list[str]) -> CommandResult:
    try:
        completed = subprocess.run(
            command,
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=30,
        )
    except (OSError, subprocess.SubprocessError):
        return CommandResult(1)
    return CommandResult(completed.returncode, completed.stdout, completed.stderr)


def _module_available(name: str) -> bool:
    try:
        return util.find_spec(name) is not None
    except (ImportError, AttributeError, ValueError):
        return False


def _nearest_existing_directory_is_writable(path: Path) -> bool:
    candidate = path
    while not candidate.exists() and candidate != candidate.parent:
        candidate = candidate.parent
    return candidate.is_dir() and os.access(candidate, os.W_OK)


def _json_object(value: str) -> dict[str, Any]:
    try:
        parsed = json.loads(value)
    except (json.JSONDecodeError, TypeError):
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _safe_int(value: object) -> int:
    return value if isinstance(value, int) and value >= 0 else 0


def _first_safe_line(value: str) -> str:
    return value.strip().splitlines()[0][:120] if value.strip() else ""


def sanitize_executable_name(path: str | None) -> str | None:
    """Return only an executable filename for shareable diagnostic output."""
    return Path(path).name if path else None
