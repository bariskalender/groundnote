from __future__ import annotations

from groundnote.diagnostics import sanitize_executable_name


def test_check_foundry_reports_only_executable_name() -> None:
    private_path = r"C:\Users\private-name\AppData\Local\Microsoft\WinGet\foundry.exe"

    assert sanitize_executable_name(private_path) == "foundry.exe"
    assert "private-name" not in sanitize_executable_name(private_path)
    assert sanitize_executable_name(None) is None
