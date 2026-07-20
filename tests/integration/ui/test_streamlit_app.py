from __future__ import annotations

from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from groundnote.app import get_application_context


def test_streamlit_application_starts_with_chat_first_sidebar(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("GROUNDNOTE_DATA_DIR", str(tmp_path / "app"))
    get_application_context.clear()
    app_path = Path(__file__).resolve().parents[3] / "src" / "groundnote" / "app.py"

    app = AppTest.from_file(str(app_path), default_timeout=20).run()

    assert not app.exception
    assert app.title[0].value == "GroundNote"
    assert len(app.file_uploader) == 1
    assert len(app.chat_input) == 1
    assert any(button.label == "New chat" for button in app.button)
    assert not any(button.label == "Process documents" for button in app.button)
    assert not any("Indexed documents" in header.value for header in app.subheader)
    assert not any("Retry indexing" in header.value for header in app.subheader)
    assert any(element.proto.popover.label == "⚙️" for element in app.get("popover"))
    assert any(selectbox.label == "Interface language" for selectbox in app.selectbox)
    performance = next(
        selectbox for selectbox in app.selectbox if selectbox.label == "Performance mode"
    )
    assert performance.value == "Balanced"
    assert any(subheader.value == "Documents" for subheader in app.subheader)
    language = next(
        selectbox for selectbox in app.selectbox if selectbox.label == "Interface language"
    )
    app = language.select("tr").run()
    assert not app.exception
    assert any(button.label == "Yeni sohbet" for button in app.button)
    context = get_application_context()
    embedding = context.embedding_provider
    chat = context.chat_provider
    assert getattr(embedding, "_model", None) is None
    assert getattr(chat, "_model", None) is None
    get_application_context.clear()
