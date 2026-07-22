from __future__ import annotations

import json
import socket
import sqlite3
from pathlib import Path

import pytest

from groundnote.config import Settings
from groundnote.diagnostics import (
    CheckLevel,
    CommandResult,
    run_doctor,
)


class FakeRunner:
    def __init__(
        self,
        *,
        service_running: bool = True,
        cached_aliases: set[str] | None = None,
    ) -> None:
        self.service_running = service_running
        self.cached_aliases = cached_aliases or {
            "phi-3.5-mini",
            "qwen2.5-0.5b",
            "qwen3-embedding-0.6b",
        }
        self.commands: list[tuple[str, ...]] = []

    def __call__(self, command: list[str]) -> CommandResult:
        self.commands.append(tuple(command))
        joined = " ".join(command)
        if "--version" in command and "foundry" in command[0]:
            return CommandResult(0, "0.10.2\n")
        if "--version" in command and "uv" in command[0]:
            return CommandResult(0, "uv 0.11.29\n")
        if "server status" in joined:
            return CommandResult(
                0,
                json.dumps(
                    {
                        "running": self.service_running,
                        "state": "ready" if self.service_running else "not_running",
                    }
                ),
            )
        if "cache list" in joined:
            return CommandResult(
                0,
                json.dumps(
                    {
                        "models": [
                            {"alias": alias, "cached": True}
                            for alias in sorted(self.cached_aliases)
                        ]
                    }
                ),
            )
        if " status -o json" in f" {joined}":
            return CommandResult(0, json.dumps({"models": {"loaded": 0}}))
        if "server stop" in joined:
            return CommandResult(0)
        if "status --porcelain" in joined:
            return CommandResult(0)
        return CommandResult(0)


def _settings(tmp_path: Path) -> Settings:
    settings = Settings(data_directory=tmp_path / "GroundNote data")
    settings.initialize_directories()
    assert settings.database_path is not None
    with sqlite3.connect(settings.database_path) as connection:
        connection.execute("CREATE TABLE readiness (id INTEGER PRIMARY KEY)")
    return settings


def _finder(name: str) -> str | None:
    return f"C:/tools/{name}.exe" if name in {"uv", "foundry", "git"} else None


def _checks_by_name(report: object) -> dict[str, object]:
    return {check.name: check for check in report.checks}  # type: ignore[attr-defined]


def test_doctor_reports_healthy_environment(tmp_path: Path) -> None:
    report = run_doctor(
        settings=_settings(tmp_path),
        repository_root=Path(__file__).resolve().parents[2],
        command_runner=FakeRunner(),
        executable_finder=_finder,
        operating_system="Windows",
        python_version=(3, 11, 15),
        port=18501,
    )

    assert report.ready
    assert report.exit_code == 0
    assert "Result: ready" in report.render()


def test_doctor_reports_missing_foundry_cli(tmp_path: Path) -> None:
    def finder(name: str) -> str | None:
        return None if name == "foundry" else f"C:/tools/{name}.exe"

    report = run_doctor(
        settings=_settings(tmp_path),
        repository_root=Path(__file__).resolve().parents[2],
        command_runner=FakeRunner(),
        executable_finder=finder,
        operating_system="Windows",
        python_version=(3, 11, 0),
        port=18502,
    )

    assert _checks_by_name(report)["Foundry Local CLI"].level is CheckLevel.ERROR
    assert not report.ready


def test_doctor_reports_service_unavailable_and_restores_initial_state(tmp_path: Path) -> None:
    runner = FakeRunner(service_running=False)

    report = run_doctor(
        settings=_settings(tmp_path),
        repository_root=Path(__file__).resolve().parents[2],
        command_runner=runner,
        executable_finder=_finder,
        operating_system="Windows",
        python_version=(3, 11, 0),
        port=18503,
    )

    assert _checks_by_name(report)["Foundry service"].level is CheckLevel.ERROR
    assert any("server stop" in " ".join(command) for command in runner.commands)


def test_doctor_reports_missing_required_model(tmp_path: Path) -> None:
    runner = FakeRunner(cached_aliases={"phi-3.5-mini", "qwen2.5-0.5b"})

    report = run_doctor(
        settings=_settings(tmp_path),
        repository_root=Path(__file__).resolve().parents[2],
        command_runner=runner,
        executable_finder=_finder,
        operating_system="Windows",
        python_version=(3, 11, 0),
        port=18504,
    )

    check = _checks_by_name(report)["Required models"]
    assert check.level is CheckLevel.ERROR
    assert "qwen3-embedding-0.6b" in check.message


def test_doctor_reports_unwritable_data_directory(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    settings = Settings(data_directory=tmp_path / "blocked")
    monkeypatch.setattr(
        "groundnote.diagnostics._nearest_existing_directory_is_writable", lambda _path: False
    )

    report = run_doctor(
        settings=settings,
        repository_root=Path(__file__).resolve().parents[2],
        command_runner=FakeRunner(),
        executable_finder=_finder,
        operating_system="Windows",
        python_version=(3, 11, 0),
        port=18505,
    )

    assert _checks_by_name(report)["Data directory"].level is CheckLevel.ERROR


def test_doctor_reports_occupied_port(tmp_path: Path) -> None:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as listener:
        listener.bind(("127.0.0.1", 0))
        port = listener.getsockname()[1]
        report = run_doctor(
            settings=_settings(tmp_path),
            repository_root=Path(__file__).resolve().parents[2],
            command_runner=FakeRunner(),
            executable_finder=_finder,
            operating_system="Windows",
            python_version=(3, 11, 0),
            port=port,
        )

    assert _checks_by_name(report)["Streamlit port"].level is CheckLevel.ERROR


def test_doctor_output_does_not_expose_sensitive_values(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    secret = "do-not-print-this-secret"
    monkeypatch.setenv("GROUNDNOTE_API_KEY", secret)
    settings = _settings(tmp_path / "private-user-folder")

    report = run_doctor(
        settings=settings,
        repository_root=Path(__file__).resolve().parents[2],
        command_runner=FakeRunner(),
        executable_finder=_finder,
        operating_system="Windows",
        python_version=(3, 11, 0),
        port=18506,
    )
    rendered = report.render()

    assert secret not in rendered
    assert str(settings.data_directory) not in rendered
