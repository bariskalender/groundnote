"""Centralized localized UI text."""

from __future__ import annotations

LanguageCode = str


TEXT: dict[str, dict[str, str]] = {
    "en": {
        "new_chat": "New chat",
        "upload_documents": "Upload documents",
        "documents": "Documents",
        "upload_help": "Select PDF, DOCX, TXT, or Markdown files. Processing starts automatically.",
        "upload_limit": "Maximum file size: {size} MB. OCR is not supported.",
        "selected_files": "{count} file(s) selected",
        "sources": "Sources",
        "ask_placeholder": "Ask about your documents",
        "no_indexed_documents": "No indexed documents",
        "no_relevant_evidence": "No relevant evidence",
        "foundry_status": "Foundry status",
        "performance_mode": "Performance mode",
        "settings": "Settings",
        "settings_help": "Open settings",
        "duplicate_document": "Duplicate document",
        "indexing": "Indexing",
        "waiting": "Waiting",
        "validating_upload": "Validating",
        "processing": "Processing",
        "ready": "Ready",
        "failed": "Failed",
        "duplicate": "This file is already uploaded, so it was not processed again.",
        "retry": "Retry",
        "reselect_retry": "Select this file again to retry.",
        "unload_models": "Unload local models",
        "language": "Language",
        "interface_language": "Interface language",
        "answer_language": "Answer language",
        "answer_auto": "Same as question",
        "answer_english": "English",
        "answer_turkish": "Turkish",
        "balanced": "Balanced",
        "fast": "Fast",
        "memory_saver": "Memory saver",
        "models_unloaded": "Local models unloaded",
        "preparing_documents": "{count} document(s) are being prepared",
        "no_documents": "No documents added yet",
        "source_documents": "Documents",
        "source_file_types": "File types",
        "all_sources_help": "Leave empty to search all ready documents.",
        "active_sources": "{count} active source(s)",
        "local_notice": "Local-only. Cached models run on this computer. OCR is not supported.",
        "assistant_greeting": "Upload documents in the sidebar, then ask questions here.",
        "searching": "Searching documents",
        "reading": "Reading relevant sections",
        "generating": "Generating answer",
        "validating": "Validating sources",
        "technical_details": "Technical details",
        "show_debug_details": "Show debug details",
        "delete_document": "Remove",
        "confirm_delete_document": "Remove this document?",
        "delete_confirm": "Remove",
        "delete_cancel": "Cancel",
        "document_deleted": (
            "Removed {filename} from GroundNote. The original file on disk was not deleted."
        ),
        "operation_busy_question": (
            "A document operation is running. Please wait until indexing finishes before asking a question."
        ),
        "operation_busy_indexing": (
            "A document operation is running. Please wait for it to finish before starting another operation."
        ),
        "operation_reset": (
            "Something went wrong while completing the operation. "
            "The state was reset, so you can try again."
        ),
        "memory_saver_notice": (
            "Memory saver unloads models after each operation and increases latency."
        ),
    },
    "tr": {
        "new_chat": "Yeni sohbet",
        "upload_documents": "Belgeleri yükle",
        "documents": "Belgeler",
        "upload_help": ("PDF, DOCX, TXT veya Markdown dosyalarını seçin. İşleme otomatik başlar."),
        "upload_limit": "En büyük dosya boyutu: {size} MB. OCR desteklenmez.",
        "selected_files": "{count} dosya seçildi",
        "sources": "Kaynaklar",
        "ask_placeholder": "Belgelerin hakkında soru sor",
        "no_indexed_documents": "İndeksli belge yok",
        "no_relevant_evidence": "İlgili kanıt yok",
        "foundry_status": "Foundry durumu",
        "performance_mode": "Performans modu",
        "settings": "Ayarlar",
        "settings_help": "Ayarları aç",
        "duplicate_document": "Tekrarlanan belge",
        "indexing": "İndeksleniyor",
        "waiting": "Bekliyor",
        "validating_upload": "Doğrulanıyor",
        "processing": "İşleniyor",
        "ready": "Hazır",
        "failed": "Başarısız",
        "duplicate": "Bu dosya zaten yüklü olduğu için tekrar işlenmedi.",
        "retry": "Tekrar dene",
        "reselect_retry": "Tekrar denemek için bu dosyayı yeniden seçin.",
        "unload_models": "Yerel modelleri boşalt",
        "language": "Dil",
        "interface_language": "Arayüz dili",
        "answer_language": "Yanıt dili",
        "answer_auto": "Soruyla aynı",
        "answer_english": "İngilizce",
        "answer_turkish": "Türkçe",
        "balanced": "Dengeli",
        "fast": "Hızlı",
        "memory_saver": "Bellek tasarrufu",
        "models_unloaded": "Yerel modeller boşaltıldı",
        "preparing_documents": "{count} belge hazırlanıyor",
        "no_documents": "Henüz belge eklenmedi",
        "source_documents": "Belgeler",
        "source_file_types": "Dosya türleri",
        "all_sources_help": "Tüm hazır belgelerde aramak için boş bırakın.",
        "active_sources": "{count} etkin kaynak",
        "local_notice": "Yalnızca yerel. Hazır modeller bu bilgisayarda çalışır. OCR desteklenmez.",
        "assistant_greeting": "Belgelerini kenar çubuğundan yükle, sonra burada soru sor.",
        "searching": "Belgeler aranıyor",
        "reading": "İlgili bölümler okunuyor",
        "generating": "Yanıt üretiliyor",
        "validating": "Kaynaklar doğrulanıyor",
        "technical_details": "Teknik ayrıntılar",
        "operation_reset": (
            "İşlem sırasında bir sorun oluştu. Durum sıfırlandı; tekrar deneyebilirsiniz."
        ),
        "memory_saver_notice": (
            "Bellek tasarrufu her işlemden sonra modelleri boşaltır ve gecikmeyi artırır."
        ),
    },
}

TR_EXTRA_TEXT: dict[str, str] = {
    "show_debug_details": "Geliştirici detaylarını göster",
    "delete_document": "Kaldır",
    "confirm_delete_document": "Bu belge kaldırılsın mı?",
    "delete_confirm": "Kaldır",
    "delete_cancel": "İptal",
    "document_deleted": "{filename} GroundNote içinden kaldırıldı. Diskteki özgün dosya silinmedi.",
    "operation_busy_question": "Belge işleniyor. Lütfen indeksleme tamamlandıktan sonra soru sorun.",
    "operation_busy_indexing": (
        "Bir belge işlemi çalışıyor. Lütfen yeni işlem başlatmadan önce bitmesini bekleyin."
    ),
}


def t(key: str, language: LanguageCode) -> str:
    """Return localized UI text with English fallback."""
    if language == "tr" and key in TR_EXTRA_TEXT:
        return TR_EXTRA_TEXT[key]
    language_map = TEXT.get(language, TEXT["en"])
    return language_map.get(key, TEXT["en"].get(key, key))
