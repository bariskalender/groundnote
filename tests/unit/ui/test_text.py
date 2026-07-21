from __future__ import annotations

from groundnote.ui.text import t


def test_phase_eight_knowledge_base_text_is_localized() -> None:
    assert t("knowledge_base", "en") == "Knowledge Base"
    assert t("knowledge_base", "tr") == "Bilgi Tabanı"
    assert t("reindex_document", "en") == "Re-index"
    assert t("reindex_document", "tr") == "Yeniden indeksle"
    assert t("duplicate", "en") == "This file is already indexed."
    assert t("duplicate", "tr") == "Bu dosya zaten indekslenmiş."
    assert t("delete_document", "en") == "Remove"
    assert t("delete_document", "tr") == "Kaldır"
    assert "re-indexed successfully" in t("document_reindexed", "en")
    assert "başarıyla yeniden indekslendi" in t("document_reindexed", "tr")
    assert "Another document operation" in t("operation_busy_upload", "en")
    assert "Başka bir belge işlemi" in t("operation_busy_upload", "tr")
