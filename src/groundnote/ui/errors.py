"""User-safe exception mapping for the Streamlit boundary."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from groundnote.ai import FoundryCatalogError, FoundryModelUnavailableError, FoundryProviderError
from groundnote.chunking.errors import ChunkingError
from groundnote.documents import (
    CorruptDocumentError,
    DocumentError,
    DuplicateDocumentError,
    EmptyDocumentError,
    EncodingError,
    EncryptedDocumentError,
    FileTooLargeError,
    NoExtractableTextError,
    ParserNotFoundError,
    UnsafeFileError,
    UnsupportedFileTypeError,
)
from groundnote.embeddings import (
    EmbeddingError,
    EmbeddingGenerationError,
    EmbeddingModelLoadError,
    IndexingError,
)
from groundnote.rag import (
    ChatGenerationError,
    ChatModelLoadError,
    CitationValidationError,
    EmptyRagQueryError,
    InvalidChatResponseError,
    RagError,
    RagRetrievalError,
    RepeatingGenerationError,
)
from groundnote.storage import MigrationError, StorageError
from groundnote.utils import safe_log_warning


class MessageSeverity(StrEnum):
    """Supported Streamlit notice severities."""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


@dataclass(frozen=True)
class UiMessage:
    """Display-ready message without internal exception details."""

    title: str
    message: str
    severity: MessageSeverity
    remediation: str | None = None


class UiWorkflowError(RuntimeError):
    """Base class for expected UI orchestration errors."""


class NoFileSelectedError(UiWorkflowError):
    """Raised when upload processing is requested without a file."""


class NoIndexedDocumentsError(UiWorkflowError):
    """Raised when a question has no searchable source."""


class InvalidFilterError(UiWorkflowError):
    """Raised when uncontrolled filter values are invalid."""


class DatabaseBootstrapError(UiWorkflowError):
    """Raised when local settings or storage cannot initialize."""


def map_exception(error: BaseException, language: str = "en") -> UiMessage:
    """Map known failures without exposing paths, SQL, prompts, or stack traces."""
    if isinstance(error, NoFileSelectedError):
        return _message(
            language,
            ("No document selected", "Choose a supported document first.", None),
            ("Belge seçilmedi", "Önce desteklenen bir belge seçin.", None),
            MessageSeverity.INFO,
        )
    if isinstance(error, UnsupportedFileTypeError):
        return _message(
            language,
            (
                "Unsupported file type",
                "GroundNote supports PDF, DOCX, TXT, and Markdown files.",
                None,
            ),
            (
                "Desteklenmeyen dosya türü",
                "GroundNote PDF, DOCX, TXT ve Markdown dosyalarını destekler.",
                None,
            ),
            MessageSeverity.WARNING,
        )
    if isinstance(error, FileTooLargeError):
        return _message(
            language,
            (
                "File is too large",
                "The document exceeds the configured local upload limit.",
                "Choose a smaller document or adjust the local upload setting.",
            ),
            (
                "Dosya çok büyük",
                "Belge, yapılandırılmış yerel yükleme sınırını aşıyor.",
                "Daha küçük bir belge seçin veya yerel yükleme ayarını değiştirin.",
            ),
            MessageSeverity.WARNING,
        )
    if isinstance(error, EmptyDocumentError):
        return _message(
            language,
            ("Empty document", "The selected document has no content.", None),
            ("Boş belge", "Seçilen belgede içerik bulunmuyor.", None),
            MessageSeverity.WARNING,
        )
    if isinstance(error, UnsafeFileError):
        return _message(
            language,
            (
                "Unsafe filename",
                "The selected filename cannot be processed safely.",
                "Rename the file and try again.",
            ),
            (
                "Güvenli olmayan dosya adı",
                "Seçilen dosya adı güvenli biçimde işlenemiyor.",
                "Dosyanın adını değiştirip tekrar deneyin.",
            ),
            MessageSeverity.WARNING,
        )
    if isinstance(error, EncryptedDocumentError):
        return _message(
            language,
            (
                "Encrypted PDF",
                "Encrypted PDF files are not supported.",
                "Use an unencrypted local copy.",
            ),
            (
                "Şifreli PDF",
                "Şifreli PDF dosyaları desteklenmiyor.",
                "Şifresiz bir yerel kopya kullanın.",
            ),
            MessageSeverity.WARNING,
        )
    if isinstance(error, NoExtractableTextError):
        return _message(
            language,
            (
                "No readable text",
                "This PDF appears to be image-based. OCR is not available in the MVP, so text "
                "could not be extracted.",
                "Use a text-based PDF or another supported document format.",
            ),
            (
                "Okunabilir metin yok",
                "Bu PDF görüntü tabanlı görünüyor. MVP sürümünde OCR olmadığı için metin "
                "çıkarılamadı.",
                "Metin tabanlı PDF veya desteklenen başka bir belge biçimi kullanın.",
            ),
            MessageSeverity.WARNING,
        )
    if isinstance(error, CorruptDocumentError):
        return _message(
            language,
            (
                "Unreadable document",
                "The document appears to be corrupt or invalid.",
                "Open the source file locally and export a fresh copy.",
            ),
            (
                "Okunamayan belge",
                "Belge bozuk veya geçersiz görünüyor.",
                "Kaynak dosyayı yerel olarak açıp yeni bir kopya dışa aktarın.",
            ),
            MessageSeverity.ERROR,
        )
    if isinstance(error, EncodingError):
        return _message(
            language,
            (
                "Unsupported text encoding",
                "GroundNote could not read this text document as UTF-8.",
                "Save the document as UTF-8 and try again.",
            ),
            (
                "Desteklenmeyen metin kodlaması",
                "GroundNote bu metin belgesini UTF-8 olarak okuyamadı.",
                "Belgeyi UTF-8 olarak kaydedip tekrar deneyin.",
            ),
            MessageSeverity.WARNING,
        )
    if isinstance(error, ParserNotFoundError):
        return _message(
            language,
            (
                "Document reader unavailable",
                "GroundNote does not have a reader for this document type.",
                None,
            ),
            (
                "Belge okuyucu kullanılamıyor",
                "GroundNote bu belge türü için bir okuyucuya sahip değil.",
                None,
            ),
            MessageSeverity.ERROR,
        )
    if isinstance(error, DuplicateDocumentError):
        return _message(
            language,
            (
                "Document already added",
                "This document has already been added to GroundNote.",
                None,
            ),
            ("Belge zaten eklendi", "Bu belge GroundNote'a daha önce eklenmiş.", None),
            MessageSeverity.INFO,
        )
    if isinstance(error, ChunkingError):
        return _message(
            language,
            (
                "Document processing failed",
                "GroundNote could not create safe searchable sections for this document.",
                None,
            ),
            (
                "Belge işlenemedi",
                "GroundNote bu belge için güvenli aranabilir bölümler oluşturamadı.",
                None,
            ),
            MessageSeverity.ERROR,
        )
    if isinstance(
        error,
        (EmbeddingModelLoadError, ChatModelLoadError, FoundryModelUnavailableError),
    ):
        return _message(
            language,
            (
                "Local model unavailable",
                "The required Foundry Local model could not be loaded.",
                "Confirm the model is cached and run `foundry server start` in a terminal.",
            ),
            (
                "Yerel model kullanılamıyor",
                "Gerekli Foundry Local modeli yüklenemedi.",
                "Modelin önbellekte olduğunu doğrulayın ve terminalde "
                "`foundry server start` çalıştırın.",
            ),
            MessageSeverity.ERROR,
        )
    if isinstance(error, (FoundryCatalogError, FoundryProviderError)):
        return _message(
            language,
            (
                "Foundry Local unavailable",
                "GroundNote could not reach the local AI runtime.",
                "Run `foundry server start` in a terminal, then try again.",
            ),
            (
                "Foundry Local kullanılamıyor",
                "GroundNote yerel AI çalışma zamanına ulaşamadı.",
                "Terminalde `foundry server start` çalıştırıp tekrar deneyin.",
            ),
            MessageSeverity.ERROR,
        )
    if isinstance(error, (IndexingError, EmbeddingGenerationError)):
        return _message(
            language,
            (
                "Indexing failed",
                "The document was saved but its local search index could not be completed.",
                "Check Foundry Local, then retry this document.",
            ),
            (
                "İndeksleme başarısız",
                "Belge kaydedildi ancak yerel arama indeksi tamamlanamadı.",
                "Foundry Local durumunu kontrol edip bu belgeyi tekrar deneyin.",
            ),
            MessageSeverity.ERROR,
        )
    if isinstance(error, EmbeddingError):
        return _message(
            language,
            (
                "Local embedding failed",
                "GroundNote could not complete the local embedding operation.",
                None,
            ),
            (
                "Yerel gömme işlemi başarısız",
                "GroundNote yerel gömme işlemini tamamlayamadı.",
                None,
            ),
            MessageSeverity.ERROR,
        )
    if isinstance(error, EmptyRagQueryError):
        return _message(
            language,
            ("Empty question", "Enter a question before asking GroundNote.", None),
            ("Boş soru", "GroundNote'a sormadan önce bir soru girin.", None),
            MessageSeverity.INFO,
        )
    if isinstance(error, NoIndexedDocumentsError):
        return _message(
            language,
            (
                "No indexed documents",
                "Add and index at least one document before asking a question.",
                None,
            ),
            (
                "Hazır belge yok",
                "Soru sormadan önce en az bir belge ekleyip hazırlanmasını bekleyin.",
                None,
            ),
            MessageSeverity.INFO,
        )
    if isinstance(error, InvalidFilterError):
        return _message(
            language,
            (
                "Invalid source filter",
                "One or more selected sources are no longer available.",
                "Refresh the page and choose the sources again.",
            ),
            (
                "Geçersiz kaynak filtresi",
                "Seçilen kaynaklardan biri veya birkaçı artık kullanılamıyor.",
                "Sayfayı yenileyip kaynakları yeniden seçin.",
            ),
            MessageSeverity.WARNING,
        )
    if isinstance(error, RagRetrievalError):
        return _message(
            language,
            ("Search failed", "GroundNote could not search the local document index.", None),
            ("Arama başarısız", "GroundNote yerel belge indeksinde arama yapamadı.", None),
            MessageSeverity.ERROR,
        )
    if isinstance(error, RepeatingGenerationError):
        return _message(
            language,
            (
                "Repeating answer detected",
                "A repeating generation was detected while creating the answer. "
                "Please try a narrower question.",
                None,
            ),
            (
                "Tekrarlayan yanıt algılandı",
                "Yanıt oluşturulurken tekrar eden bir çıktı algılandı. Lütfen soruyu biraz "
                "daha daraltarak tekrar deneyin.",
                None,
            ),
            MessageSeverity.WARNING,
        )
    if isinstance(error, (ChatGenerationError, InvalidChatResponseError)):
        return _message(
            language,
            (
                "Answer generation failed",
                "The local model could not produce a safe grounded answer.",
                "Try a shorter or more specific question.",
            ),
            (
                "Yanıt üretilemedi",
                "Yerel model güvenli ve belgelenmiş bir yanıt üretemedi.",
                "Daha kısa veya daha belirli bir soru deneyin.",
            ),
            MessageSeverity.ERROR,
        )
    if isinstance(error, CitationValidationError):
        return _message(
            language,
            (
                "Citation validation failed",
                "The answer was not shown because its sources could not be verified.",
                "Try asking the question again.",
            ),
            (
                "Kaynak doğrulaması başarısız",
                "Kaynakları doğrulanamadığı için yanıt gösterilmedi.",
                "Soruyu tekrar sormayı deneyin.",
            ),
            MessageSeverity.WARNING,
        )
    if isinstance(error, RagError):
        return _message(
            language,
            (
                "Question could not be completed",
                "The question could not be processed safely by the local RAG workflow.",
                "Try a shorter or more specific question.",
            ),
            (
                "Soru tamamlanamadı",
                "Soru yerel RAG akışı tarafından güvenli biçimde işlenemedi.",
                "Daha kısa veya daha belirli bir soru deneyin.",
            ),
            MessageSeverity.WARNING,
        )
    if isinstance(error, DocumentError):
        return _message(
            language,
            (
                "Document processing failed",
                "GroundNote could not safely process this document.",
                None,
            ),
            (
                "Belge işlenemedi",
                "GroundNote bu belgeyi güvenli biçimde işleyemedi.",
                None,
            ),
            MessageSeverity.ERROR,
        )
    if isinstance(error, (StorageError, MigrationError, DatabaseBootstrapError)):
        return _message(
            language,
            (
                "Local database unavailable",
                "GroundNote could not access its local document database.",
                "Close other GroundNote windows and restart the application.",
            ),
            (
                "Yerel veritabanı kullanılamıyor",
                "GroundNote yerel belge veritabanına erişemedi.",
                "Diğer GroundNote pencerelerini kapatıp uygulamayı yeniden başlatın.",
            ),
            MessageSeverity.ERROR,
        )
    if isinstance(error, TimeoutError):
        return _message(
            language,
            (
                "Operation timed out",
                "The local operation did not finish in time.",
                "Try again after checking Foundry Local.",
            ),
            (
                "İşlem zaman aşımına uğradı",
                "Yerel işlem zamanında tamamlanmadı.",
                "Foundry Local durumunu kontrol edip tekrar deneyin.",
            ),
            MessageSeverity.ERROR,
        )
    return _message(
        language,
        (
            "Operation failed",
            "Something went wrong while completing the operation. "
            "The state was reset, so you can try again.",
            None,
        ),
        (
            "İşlem başarısız",
            "İşlem sırasında bir sorun oluştu. Durum sıfırlandı; tekrar deneyebilirsiniz.",
            None,
        ),
        MessageSeverity.ERROR,
    )


def safe_failure_message(
    error: BaseException,
    *,
    logger: Any,
    event: str,
    language: str = "en",
) -> UiMessage:
    """Preserve and map the original failure even when the logger itself is broken."""
    original = error
    safe_log_warning(logger, event, error_type=type(original).__name__)
    return map_exception(original, language)


def _message(
    language: str,
    english: tuple[str, str, str | None],
    turkish: tuple[str, str, str | None],
    severity: MessageSeverity,
) -> UiMessage:
    title, message, remediation = turkish if language == "tr" else english
    return UiMessage(title, message, severity, remediation)
