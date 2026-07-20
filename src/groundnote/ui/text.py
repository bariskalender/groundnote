"""Centralized localized UI text."""

from __future__ import annotations

LanguageCode = str


TEXT: dict[str, dict[str, str]] = {
    "en": {
        "new_chat": "New chat",
        "upload_documents": "Upload documents",
        "process_documents": "Process documents",
        "indexed_documents": "Indexed documents",
        "sources": "Sources",
        "ask_placeholder": "Ask about your documents",
        "no_indexed_documents": "No indexed documents",
        "no_relevant_evidence": "No relevant evidence",
        "foundry_status": "Foundry status",
        "performance_mode": "Performance mode",
        "settings": "Settings",
        "duplicate_document": "Duplicate document",
        "indexing": "Indexing",
        "ready": "Ready",
        "failed": "Failed",
        "retry": "Retry indexing",
        "unload_models": "Unload local models",
        "language": "Language",
        "local_notice": "Local-only. Cached models run on this computer. OCR is not supported.",
        "assistant_greeting": "Upload documents in the sidebar, then ask questions here.",
        "searching": "Searching documents",
        "reading": "Reading relevant sections",
        "generating": "Generating answer",
        "validating": "Validating sources",
        "technical_details": "Technical details",
        "memory_saver_notice": (
            "Memory saver unloads models after each operation and increases latency."
        ),
    },
    "tr": {
        "new_chat": "Yeni sohbet",
        "upload_documents": "Belgeleri yükle",
        "process_documents": "Belgeleri işle",
        "indexed_documents": "İndeksli belgeler",
        "sources": "Kaynaklar",
        "ask_placeholder": "Belgelerin hakkında soru sor",
        "no_indexed_documents": "İndeksli belge yok",
        "no_relevant_evidence": "İlgili kanıt yok",
        "foundry_status": "Foundry durumu",
        "performance_mode": "Performans modu",
        "settings": "Ayarlar",
        "duplicate_document": "Tekrarlanan belge",
        "indexing": "İndeksleniyor",
        "ready": "Hazır",
        "failed": "Başarısız",
        "retry": "İndekslemeyi tekrar dene",
        "unload_models": "Yerel modelleri boşalt",
        "language": "Dil",
        "local_notice": "Yalnızca yerel. Hazır modeller bu bilgisayarda çalışır. OCR desteklenmez.",
        "assistant_greeting": "Belgelerini kenar çubuğundan yükle, sonra burada soru sor.",
        "searching": "Belgeler aranıyor",
        "reading": "İlgili bölümler okunuyor",
        "generating": "Yanıt üretiliyor",
        "validating": "Kaynaklar doğrulanıyor",
        "technical_details": "Teknik ayrıntılar",
        "memory_saver_notice": (
            "Bellek tasarrufu her işlemden sonra modelleri boşaltır ve gecikmeyi artırır."
        ),
    },
}


def t(key: str, language: LanguageCode) -> str:
    """Return localized UI text with English fallback."""
    language_map = TEXT.get(language, TEXT["en"])
    return language_map.get(key, TEXT["en"].get(key, key))
