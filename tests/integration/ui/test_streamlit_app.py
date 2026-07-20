from __future__ import annotations

from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from groundnote.app import get_application_context


def test_streamlit_application_starts_with_documents_and_ask_views(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("GROUNDNOTE_DATA_DIR", str(tmp_path / "app"))
    get_application_context.clear()
    app_path = Path(__file__).resolve().parents[3] / "src" / "groundnote" / "app.py"

    app = AppTest.from_file(str(app_path), default_timeout=20).run()

    assert not app.exception
    assert app.title[0].value == "GroundNote"
    assert any(header.value == "Documents" for header in app.header)
    assert len(app.file_uploader) == 1
    assert any("No documents" in info.value for info in app.info)

    app.radio[0].set_value("Ask GroundNote").run()

    assert not app.exception
    assert any(header.value == "Ask GroundNote" for header in app.header)
    assert any("No indexed documents" in info.value for info in app.info)
    context = get_application_context()
    embedding = context.embedding_provider
    chat = context.chat_provider
    assert getattr(embedding, "_model", None) is None
    assert getattr(chat, "_model", None) is None
    get_application_context.clear()
