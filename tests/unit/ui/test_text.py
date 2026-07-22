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
    assert t("operation_busy_upload", "en") == (
        "GroundNote is indexing a document. Upload another file after it finishes."
    )
    assert t("operation_busy_upload", "tr") == (
        "GroundNote bir belgeyi indeksliyor. İşlem tamamlandıktan sonra başka bir dosya yükleyin."
    )


def test_phase_nine_one_recovery_and_cleanup_text_is_localized() -> None:
    keys = (
        "retry_required",
        "document_not_ready",
        "indexing_interrupted",
        "managed_copy_cleanup_warning",
        "managed_copies_cleanup_warning",
    )
    for key in keys:
        assert t(key, "en") != key
        assert t(key, "tr") != key
    assert "managed copy" in t("confirm_delete_document", "en")
    assert "yönettiği kopyayı" in t("confirm_delete_document", "tr")
