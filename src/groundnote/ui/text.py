"""Centralized localized UI text."""

from __future__ import annotations

LanguageCode = str


TEXT: dict[str, dict[str, str]] = {
    "en": {
        "new_chat": "New chat",
        "upload_documents": "Upload documents",
        "documents": "Documents",
        "knowledge_base": "Knowledge Base",
        "indexed_documents": "Indexed documents",
        "upload_help": "Select PDF, DOCX, TXT, or Markdown files. Processing starts automatically.",
        "upload_limit": "Maximum file size: {size} MB. OCR is not supported.",
        "selected_files": "{count} file(s) selected",
        "sources": "Sources",
        "ask_placeholder": "Ask about your documents",
        "no_indexed_documents": "No indexed documents",
        "no_relevant_evidence": "No relevant evidence",
        "foundry_status": "Foundry status",
        "groundnote_not_ready": (
            "GroundNote is not ready yet. Run `scripts/doctor.ps1` to see what is missing."
        ),
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
        "retry_required": "Interrupted / Retry required",
        "document_not_ready": "This document is not ready and will not be used for answers.",
        "indexing_interrupted": (
            "Indexing was interrupted. Re-index this document to make it available."
        ),
        "duplicate": "This file is already indexed.",
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
        "confirm_delete_document": (
            "This removes the document from GroundNote's index and deletes GroundNote's "
            "managed copy. The original file you selected is not deleted."
        ),
        "delete_confirm": "Remove",
        "delete_cancel": "Cancel",
        "document_deleted": (
            "Removed {filename} and GroundNote's managed copy. The original selected file "
            "was not deleted."
        ),
        "managed_copy_cleanup_warning": (
            "The document was removed from GroundNote, but its managed copy could not be "
            "deleted. The original selected file was not touched."
        ),
        "reindex_document": "Re-index",
        "reindexing_document": "Re-indexing {filename}",
        "document_reindexed": "{filename} was re-indexed successfully.",
        "clear_all_documents": "Clear all documents",
        "confirm_clear_all_documents": "Clear all documents from GroundNote's index?",
        "clear_all_warning": (
            "This removes all represented documents from GroundNote's index and deletes "
            "GroundNote's managed copies. Original files you selected are not deleted."
        ),
        "clear_all_confirm": "Clear all",
        "documents_cleared": (
            "Removed {count} document(s) and their GroundNote-managed copies. Original "
            "selected files were not deleted."
        ),
        "managed_copies_cleanup_warning": (
            "Removed {count} document(s) from GroundNote, but {warning_count} managed "
            "copy/copies could not be deleted. Original selected files were not touched."
        ),
        "document_metadata": "Details",
        "document_pages": "{count} page(s)",
        "document_chunks": "{count} chunk(s)",
        "document_type": "Type: {file_type}",
        "indexed_at": "Indexed: {timestamp}",
        "not_indexed_yet": "Not indexed yet",
        "current_chat": "Current chat",
        "new_chat_busy": "Wait for the current operation to finish before starting a new chat.",
        "empty_chat_no_documents": "Upload a document first, or select an indexed document.",
        "empty_chat_with_documents": "Try asking about a section, a concept, or a comparison in your indexed documents.",
        "operation_busy_question": (
            "A local operation is running. Please wait for it to finish before asking a question."
        ),
        "chat_busy_indexing": (
            "GroundNote is indexing a document. Chat will be available when indexing finishes."
        ),
        "operation_busy_indexing": (
            "A document operation is running. Please wait for it to finish before starting another operation."
        ),
        "operation_busy_upload": (
            "Another document operation is already in progress. Wait for it to finish before uploading another file."
        ),
        "operation_reset": (
            "Something went wrong while completing the operation. "
            "The state was reset, so you can try again."
        ),
        "memory_saver_notice": (
            "Memory saver unloads models after each operation and increases latency."
        ),
        "indexing_diagnostics": "Indexing diagnostics",
        "indexing_diagnostics_summary": (
            "Total: {duration} · Chunks: {chunks} · Embedding batches: {batches}"
        ),
        "indexing_model_usage": "Model load: {load_duration} · Reused: {reuse}",
        "indexing_peak_memory": "Peak GroundNote process RSS estimate: {memory:.1f} MB",
        "indexing_failed_at": "Failed during {stage}: {filename}",
        "yes": "yes",
        "no": "no",
        "index_stage_saving_upload": "Saving upload locally",
        "index_stage_validating": "Validating file",
        "index_stage_hashing": "Checking file identity",
        "index_stage_duplicate_check": "Checking for duplicates",
        "index_stage_parsing": "Extracting document text",
        "index_stage_chunking": "Creating searchable chunks",
        "index_stage_saving_chunks": "Saving document chunks",
        "index_stage_loading_embedding_model": "Loading embedding model",
        "index_stage_embedding": "Embedding chunks",
        "index_stage_saving_vectors": "Saving embeddings",
        "index_stage_fts_indexing": "Saving search index",
        "index_stage_integrity_verification": "Verifying index integrity",
        "index_stage_finalization": "Finalizing document",
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
    "groundnote_not_ready": (
        "GroundNote henüz hazır değil. Eksik bileşenleri görmek için "
        "`scripts/doctor.ps1` komutunu çalıştırın."
    ),
    "knowledge_base": "Bilgi Tabanı",
    "indexed_documents": "İndekslenmiş belgeler",
    "show_debug_details": "Geliştirici detaylarını göster",
    "delete_document": "Kaldır",
    "confirm_delete_document": (
        "Bu işlem belgeyi GroundNote indeksinden kaldırır ve GroundNote'un yönettiği kopyayı "
        "siler. Seçtiğiniz orijinal dosya silinmez."
    ),
    "delete_confirm": "Kaldır",
    "delete_cancel": "İptal",
    "document_deleted": (
        "{filename} ve GroundNote'un yönettiği kopya kaldırıldı. Seçtiğiniz orijinal dosya "
        "silinmedi."
    ),
    "managed_copy_cleanup_warning": (
        "Belge GroundNote'tan kaldırıldı ancak yönetilen kopyası silinemedi. Seçtiğiniz "
        "orijinal dosyaya dokunulmadı."
    ),
    "duplicate": "Bu dosya zaten indekslenmiş.",
    "reindex_document": "Yeniden indeksle",
    "reindexing_document": "{filename} yeniden indeksleniyor",
    "document_reindexed": "{filename} başarıyla yeniden indekslendi.",
    "clear_all_documents": "Tümünü temizle",
    "confirm_clear_all_documents": "Tüm belgeler GroundNote indeksinden kaldırılsın mı?",
    "clear_all_warning": (
        "Bu işlem temsil edilen tüm belgeleri GroundNote indeksinden kaldırır ve GroundNote'un "
        "yönettiği kopyaları siler. Seçtiğiniz orijinal dosyalar silinmez."
    ),
    "clear_all_confirm": "Tümünü temizle",
    "documents_cleared": (
        "{count} belge ve GroundNote'un yönettiği kopyaları kaldırıldı. Seçtiğiniz orijinal "
        "dosyalar silinmedi."
    ),
    "managed_copies_cleanup_warning": (
        "{count} belge GroundNote'tan kaldırıldı ancak {warning_count} yönetilen kopya "
        "silinemedi. Seçtiğiniz orijinal dosyalara dokunulmadı."
    ),
    "retry_required": "Yarıda kesildi / Yeniden deneme gerekli",
    "document_not_ready": "Bu belge hazır değil ve cevaplarda kullanılmayacak.",
    "indexing_interrupted": (
        "İndeksleme yarıda kesildi. Belgeyi kullanılabilir hâle getirmek için yeniden indeksleyin."
    ),
    "document_metadata": "Ayrıntılar",
    "document_pages": "{count} sayfa",
    "document_chunks": "{count} parça",
    "document_type": "Tür: {file_type}",
    "indexed_at": "İndeksleme: {timestamp}",
    "not_indexed_yet": "Henüz indekslenmedi",
    "current_chat": "Geçerli sohbet",
    "new_chat_busy": "Yeni sohbet başlatmadan önce mevcut işlemin bitmesini bekleyin.",
    "empty_chat_no_documents": "Önce belge yükleyin veya indekslenmiş belgelerden birini seçin.",
    "empty_chat_with_documents": "İndekslenmiş belgelerinizdeki bir bölüm, kavram veya karşılaştırma hakkında soru sorabilirsiniz.",
    "operation_busy_question": "Yerel bir işlem sürüyor. Soru sormadan önce tamamlanmasını bekleyin.",
    "chat_busy_indexing": (
        "GroundNote bir belgeyi indeksliyor. İndeksleme tamamlandığında sohbet yeniden kullanılabilir."
    ),
    "operation_busy_indexing": (
        "Bir belge işlemi çalışıyor. Lütfen yeni işlem başlatmadan önce bitmesini bekleyin."
    ),
    "operation_busy_upload": (
        "Başka bir belge işlemi devam ediyor. Yeni bir dosya yüklemeden önce işlemin tamamlanmasını bekleyin."
    ),
    "indexing_diagnostics": "İndeksleme tanılamaları",
    "indexing_diagnostics_summary": (
        "Toplam: {duration} · Parça: {chunks} · Embedding batch sayısı: {batches}"
    ),
    "indexing_model_usage": "Model yükleme: {load_duration} · Yeniden kullanıldı: {reuse}",
    "indexing_peak_memory": "Tahmini en yüksek GroundNote süreç RSS değeri: {memory:.1f} MB",
    "indexing_failed_at": "{stage} aşamasında başarısız oldu: {filename}",
    "yes": "evet",
    "no": "hayır",
    "index_stage_saving_upload": "Yüklemeyi yerel olarak kaydediyor",
    "index_stage_validating": "Dosyayı doğruluyor",
    "index_stage_hashing": "Dosya kimliğini kontrol ediyor",
    "index_stage_duplicate_check": "Tekrar eden dosyayı kontrol ediyor",
    "index_stage_parsing": "Belge metnini çıkarıyor",
    "index_stage_chunking": "Aranabilir parçaları oluşturuyor",
    "index_stage_saving_chunks": "Belge parçalarını kaydediyor",
    "index_stage_loading_embedding_model": "Embedding modelini yüklüyor",
    "index_stage_embedding": "Parçalar için embedding oluşturuyor",
    "index_stage_saving_vectors": "Embedding verilerini kaydediyor",
    "index_stage_fts_indexing": "Arama indeksini kaydediyor",
    "index_stage_integrity_verification": "İndeks bütünlüğünü doğruluyor",
    "index_stage_finalization": "Belgeyi tamamlıyor",
}


def t(key: str, language: LanguageCode) -> str:
    """Return localized UI text with English fallback."""
    if language == "tr" and key in TR_EXTRA_TEXT:
        return TR_EXTRA_TEXT[key]
    language_map = TEXT.get(language, TEXT["en"])
    return language_map.get(key, TEXT["en"].get(key, key))
