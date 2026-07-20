from __future__ import annotations

import subprocess

import pytest

from groundnote.ui.foundry_status import FoundryStatusKind, FoundryStatusService


def test_foundry_status_reports_unavailable_without_cli(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("groundnote.ui.foundry_status.shutil.which", lambda _: None)

    status = FoundryStatusService().check()

    assert status.kind is FoundryStatusKind.UNAVAILABLE
    assert status.label == "Unavailable"


@pytest.mark.parametrize(
    ("output", "returncode", "expected"),
    [
        ("Status: Ready\nLocal service: Reachable", 0, FoundryStatusKind.READY),
        ("Status: Not running", 1, FoundryStatusKind.NOT_RUNNING),
        ("preview output changed", 0, FoundryStatusKind.UNKNOWN),
    ],
)
def test_foundry_status_maps_cli_output_without_exposing_it(
    monkeypatch: pytest.MonkeyPatch,
    output: str,
    returncode: int,
    expected: FoundryStatusKind,
) -> None:
    monkeypatch.setattr("groundnote.ui.foundry_status.shutil.which", lambda _: "foundry.exe")
    monkeypatch.setattr(
        "groundnote.ui.foundry_status.subprocess.run",
        lambda *args, **kwargs: subprocess.CompletedProcess(
            args=["foundry.exe", "server", "status"],
            returncode=returncode,
            stdout=output,
            stderr="",
        ),
    )

    status = FoundryStatusService().check()

    assert status.kind is expected
    assert "Reachable" not in status.label
    assert "preview output" not in (status.instruction or "")
