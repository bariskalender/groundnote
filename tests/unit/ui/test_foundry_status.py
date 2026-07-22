from __future__ import annotations

import subprocess

import pytest

from groundnote.ui.foundry_status import (
    FoundryStatus,
    FoundryStatusKind,
    FoundryStatusService,
    localized_foundry_status,
)


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
        ("Status: Starting", 0, FoundryStatusKind.STARTING),
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


@pytest.mark.parametrize(
    ("kind", "english", "turkish"),
    [
        (FoundryStatusKind.READY, "Ready", "Hazır"),
        (FoundryStatusKind.NOT_RUNNING, "Not running", "Çalışmıyor"),
        (FoundryStatusKind.STARTING, "Starting", "Başlatılıyor"),
        (FoundryStatusKind.UNAVAILABLE, "Unavailable", "Kullanılamıyor"),
        (FoundryStatusKind.UNKNOWN, "Unknown", "Bilinmiyor"),
    ],
)
def test_foundry_status_is_localized_for_streamlit(
    kind: FoundryStatusKind,
    english: str,
    turkish: str,
) -> None:
    status = FoundryStatus(kind, english)

    assert localized_foundry_status(status, "en").label == english
    localized = localized_foundry_status(status, "tr")
    assert localized.label == turkish
    assert english not in localized.label
