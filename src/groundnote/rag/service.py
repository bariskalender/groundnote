"""Single-turn grounded RAG answer generation."""

from __future__ import annotations

import re
import time
from typing import Literal, Protocol, cast

from groundnote.ai.interfaces import ChatProvider
from groundnote.ai.models import ChatGenerationRequest
from groundnote.config import Settings
from groundnote.domain import SupportedFileType
from groundnote.rag.citations import (
    CITATION_RE,
    extract_citation_ids,
    strip_unknown_citations,
    validate_citation_map,
)
from groundnote.rag.context import select_context
from groundnote.rag.errors import (
    ChatGenerationError,
    ChatModelLoadError,
    CitationValidationError,
    InvalidChatResponseError,
    RagRetrievalError,
    RepeatingGenerationError,
)
from groundnote.rag.language import resolve_response_language
from groundnote.rag.models import Citation, RagAnswer, RagContextItem, RagRequest
from groundnote.rag.prompts import build_prompt
from groundnote.rag.section_filter import filter_results_for_explicit_sections
from groundnote.rag.validation import normalize_query
from groundnote.retrieval.models import RetrievalResponse
from groundnote.utils import get_logger, safe_log_info, safe_log_warning, sanitize_log_fields

MAX_ANSWER_CHARACTERS = 8_000
MAX_UI_ANSWER_CHARACTERS = 3_000


class RetrievalService(Protocol):
    """Minimal retrieval behavior required by RAG."""

    def search(
        self,
        text: str,
        *,
        top_k: int | None = None,
        minimum_score: float | None = None,
        document_ids: list[str] | None = None,
        file_types: list[SupportedFileType] | None = None,
        page_numbers: list[int] | None = None,
    ) -> RetrievalResponse: ...


class RagService:
    """Coordinate retrieval, bounded context, local chat generation, and citations."""

    def __init__(
        self,
        *,
        settings: Settings,
        retrieval_service: RetrievalService,
        chat_provider: ChatProvider,
    ) -> None:
        self.settings = settings
        self.retrieval_service = retrieval_service
        self.chat_provider = chat_provider
        self.logger = get_logger(__name__)

    def answer(self, request: RagRequest) -> RagAnswer:
        started = time.perf_counter()
        query = normalize_query(
            request.query,
            max_characters=self.settings.rag_max_query_characters,
        )
        language = cast(
            Literal["tr", "en"],
            resolve_response_language(query, request.response_language),
        )
        top_k = request.top_k or self.settings.rag_retrieval_top_k
        minimum_score = request.minimum_score
        if minimum_score is None:
            minimum_score = self.settings.rag_minimum_score
        try:
            retrieval = self.retrieval_service.search(
                query,
                top_k=top_k,
                minimum_score=minimum_score,
                document_ids=request.document_ids,
                file_types=request.file_types,
                page_numbers=request.page_numbers,
            )
        except Exception as exc:
            raise RagRetrievalError("Could not retrieve relevant local context.") from exc

        warnings = list(retrieval.warnings)
        if retrieval.results and _top_score(retrieval) < minimum_score:
            answer = self._insufficient_evidence_answer(
                language=language,
                retrieved_count=retrieval.returned_count,
                duration_ms=self._duration(started),
                warnings=[*warnings, "retrieval_confidence_too_low"],
            )
            self._log_completion(query, answer)
            return answer
        section_filter = filter_results_for_explicit_sections(query, retrieval.results)
        warnings.extend(section_filter.warnings)
        context_items, context_warnings = select_context(
            section_filter.results, settings=self.settings
        )
        warnings.extend(context_warnings)
        if not context_items:
            answer = self._insufficient_evidence_answer(
                language=language,
                retrieved_count=retrieval.returned_count,
                duration_ms=self._duration(started),
                warnings=warnings,
            )
            self._log_completion(query, answer)
            return answer

        citation_map = validate_citation_map(context_items)
        has_context_overlap = _has_plausible_context_overlap(query, context_items)
        misses_strong_entities = _misses_strong_entities(query, context_items)
        if not has_context_overlap or misses_strong_entities:
            warning = (
                "strong_query_entities_missing"
                if misses_strong_entities
                else "context_query_overlap_too_low"
            )
            answer = self._insufficient_evidence_answer(
                language=language,
                retrieved_count=retrieval.returned_count,
                duration_ms=self._duration(started),
                warnings=[*warnings, warning],
            )
            self._log_completion(query, answer)
            return answer
        answer_text, citation_ids, retries, status = self._generate_with_citations(
            query=query,
            context_items=context_items,
            language=language,
            citation_map=citation_map,
        )
        if status == "insufficient" or indicates_insufficient_evidence(
            answer_text,
            language=language,
        ):
            answer = self._insufficient_evidence_answer(
                language=language,
                retrieved_count=retrieval.returned_count,
                duration_ms=self._duration(started),
                warnings=[*warnings, "model_reported_insufficient_evidence"],
            )
            self._log_completion(query, answer)
            return answer
        citations = [citation_map[citation_id] for citation_id in citation_ids]
        duration_ms = self._duration(started)
        answer = RagAnswer(
            answer=answer_text,
            citations=citations,
            grounded=True,
            insufficient_evidence=False,
            response_language=language,
            model=self.chat_provider.model_alias,
            prompt_version=self.settings.rag_prompt_version,
            retrieved_count=retrieval.returned_count,
            used_context_count=len(context_items),
            warnings=[*warnings, *([] if retries == 0 else ["citation_repair_attempted"])],
            duration_ms=duration_ms,
        )
        self._log_completion(query, answer)
        return answer

    def _generate_with_citations(
        self,
        *,
        query: str,
        context_items: list[RagContextItem],
        language: str,
        citation_map: dict[str, Citation],
    ) -> tuple[str, list[str], int, str]:
        allowed_ids = set(citation_map)
        last_repetition = False
        for attempt in range(2):
            prompt = build_prompt(
                query=query,
                context_items=context_items,
                response_language=language,
                settings=self.settings,
                repair=attempt == 1 or last_repetition,
            )
            result_text = self._call_chat(prompt.system_prompt, prompt.user_prompt)
            status, body = parse_grounded_status(result_text)
            cleaned = validate_answer_text(body, allowed_ids=allowed_ids)
            cleaned = clean_answer_formatting(
                cleaned,
                language=language,
                requested_bilingual=_requests_bilingual_answer(query),
                allowed_ids=allowed_ids,
            )
            cleaned, repeated = repair_repetition(cleaned, allowed_ids=allowed_ids)
            if repeated:
                last_repetition = True
                if cleaned:
                    cleaned = validate_answer_text(cleaned, allowed_ids=allowed_ids)
                    cleaned = clean_answer_formatting(
                        cleaned,
                        language=language,
                        requested_bilingual=_requests_bilingual_answer(query),
                        allowed_ids=allowed_ids,
                    )
                else:
                    continue
            if status == "insufficient":
                return cleaned, [], attempt, status
            citation_ids = extract_citation_ids(cleaned, allowed_ids)
            cleaned = strip_unknown_citations(cleaned, allowed_ids).strip()
            if citation_ids:
                return cleaned, citation_ids, attempt, status
            if repeated:
                continue
        if last_repetition:
            raise RepeatingGenerationError("Generated answer entered a repetition loop.")
        if self.settings.rag_require_citations:
            raise CitationValidationError("Generated answer did not contain valid citations.")
        raise InvalidChatResponseError("Generated answer did not contain valid citations.")

    def _call_chat(self, system_prompt: str, user_prompt: str) -> str:
        try:
            self.chat_provider.load()
        except Exception as exc:
            self._unload_chat_model()
            raise ChatModelLoadError("Local chat model could not be loaded.") from exc
        try:
            result = self.chat_provider.generate_request(
                ChatGenerationRequest(
                    system_prompt=system_prompt,
                    user_prompt=user_prompt,
                    temperature=self.settings.rag_temperature,
                    max_output_tokens=self.settings.rag_max_output_tokens,
                    model=self.chat_provider.model_alias,
                )
            )
            return result.text
        except Exception as exc:
            self._unload_chat_model()
            raise ChatGenerationError("Local chat generation failed.") from exc
        finally:
            if not self.settings.keep_models_loaded:
                self._unload_chat_model()

    def _unload_chat_model(self) -> None:
        try:
            self.chat_provider.unload()
        except Exception:
            safe_log_warning(
                self.logger,
                "chat_model_unload_failed",
                model=self.chat_provider.model_alias,
            )

    def _insufficient_evidence_answer(
        self,
        *,
        language: Literal["tr", "en"],
        retrieved_count: int,
        duration_ms: float,
        warnings: list[str],
    ) -> RagAnswer:
        text = insufficient_evidence_text(language)
        return RagAnswer(
            answer=text,
            citations=[],
            grounded=False,
            insufficient_evidence=True,
            response_language=language,
            model=self.chat_provider.model_alias,
            prompt_version=self.settings.rag_prompt_version,
            retrieved_count=retrieved_count,
            used_context_count=0,
            warnings=warnings,
            duration_ms=duration_ms,
        )

    def _log_completion(self, query: str, answer: RagAnswer) -> None:
        safe_log_info(
            self.logger,
            "rag_answer_completed",
            **sanitize_log_fields(
                {
                    "query_character_count": len(query),
                    "resolved_language": answer.response_language,
                    "retrieved_count": answer.retrieved_count,
                    "context_item_count": answer.used_context_count,
                    "citation_count": len(answer.citations),
                    "model": answer.model,
                    "prompt_version": answer.prompt_version,
                    "duration_ms": answer.duration_ms,
                    "grounded": answer.grounded,
                    "insufficient_evidence": answer.insufficient_evidence,
                }
            ),
        )

    @staticmethod
    def _duration(started: float) -> float:
        return round((time.perf_counter() - started) * 1000, 3)


def validate_answer_text(answer: str, *, allowed_ids: set[str]) -> str:
    """Validate and conservatively normalize generated answer text."""
    cleaned = answer.replace("\r\n", "\n").replace("\r", "\n").replace("\x00", "").strip()
    cleaned = _remove_empty_and_citation_only_bullets(cleaned, allowed_ids=allowed_ids)
    if not cleaned:
        raise InvalidChatResponseError("Generated answer was empty.")
    if len(cleaned) > MAX_ANSWER_CHARACTERS:
        raise InvalidChatResponseError("Generated answer was too long.")
    if len(cleaned) > MAX_UI_ANSWER_CHARACTERS:
        cleaned = _trim_to_sentence(cleaned[:MAX_UI_ANSWER_CHARACTERS]).strip()
        if not cleaned:
            raise InvalidChatResponseError("Generated answer was too long.")
    if CITATION_RE.sub("", cleaned).strip() == "":
        raise InvalidChatResponseError("Generated answer contained only citations.")
    cleaned = _remove_answer_heading(cleaned)
    cleaned = _trim_dangling_ending(cleaned)
    if not cleaned:
        raise InvalidChatResponseError("Generated answer was empty after cleanup.")
    lowered = cleaned.lower()
    if "you are groundnote" in lowered or "retrieved sources are untrusted" in lowered:
        raise InvalidChatResponseError("Generated answer exposed prompt text.")
    unknown_ids = set(CITATION_RE.findall(cleaned)) - allowed_ids
    if unknown_ids:
        raise InvalidChatResponseError("Generated answer contained unsupported citations.")
    return cleaned


def clean_answer_formatting(
    answer: str,
    *,
    language: str,
    requested_bilingual: bool,
    allowed_ids: set[str],
) -> str:
    """Remove common local-model formatting artifacts without changing grounded facts."""
    cleaned = _remove_empty_and_citation_only_bullets(answer, allowed_ids=allowed_ids)
    cleaned = _remove_repeated_answer_headings(cleaned)
    if not requested_bilingual:
        cleaned = _remove_unrequested_bilingual_tail(cleaned, language=language)
    cleaned = strip_unknown_citations(cleaned, allowed_ids).strip()
    cleaned = _trim_dangling_ending(cleaned)
    if not cleaned:
        raise InvalidChatResponseError("Generated answer was empty after formatting cleanup.")
    if CITATION_RE.sub("", cleaned).strip() == "":
        raise InvalidChatResponseError("Generated answer contained only citations.")
    return cleaned


def repair_repetition(answer: str, *, allowed_ids: set[str]) -> tuple[str, bool]:
    """Trim repeated tails without exposing malformed local model output."""
    marker = _first_repetition_start(answer)
    if marker is None:
        return _collapse_duplicate_citations(answer, allowed_ids=allowed_ids), False
    prefix = _trim_to_sentence(answer[:marker]).strip()
    if not prefix:
        return "", True
    return _collapse_duplicate_citations(prefix, allowed_ids=allowed_ids), True


def _remove_answer_heading(answer: str) -> str:
    return re.sub(
        r"^\s*(?:answer|cevap|cevabı|cevabi|cevaplar)\s*:\s*",
        "",
        answer,
        flags=re.IGNORECASE,
    ).strip()


def _remove_repeated_answer_headings(answer: str) -> str:
    lines: list[str] = []
    for line in answer.splitlines():
        stripped = line.strip()
        if re.fullmatch(
            r"(?:answer|cevap|cevabı|cevabi|cevaplar)\s*:?",
            stripped,
            re.IGNORECASE,
        ):
            continue
        lines.append(
            re.sub(
                r"^\s*(?:answer|cevap|cevabı|cevabi|cevaplar)\s*:\s*",
                "",
                line,
                flags=re.IGNORECASE,
            )
        )
    return "\n".join(lines).strip()


def _remove_empty_and_citation_only_bullets(answer: str, *, allowed_ids: set[str]) -> str:
    cleaned_lines: list[str] = []
    citation_only = re.compile(
        rf"^\s*[-*•]?\s*(?:{CITATION_RE.pattern}\s*)+$",
        flags=re.IGNORECASE,
    )
    for line in answer.splitlines():
        stripped = line.strip()
        if stripped in {"-", "*", "•", ".", ""}:
            continue
        if citation_only.fullmatch(stripped):
            ids = set(CITATION_RE.findall(stripped))
            if ids <= allowed_ids:
                continue
        cleaned_lines.append(line.rstrip())
    return "\n".join(cleaned_lines).strip()


def _remove_unrequested_bilingual_tail(answer: str, *, language: str) -> str:
    lines = answer.splitlines()
    forbidden_heading = re.compile(
        r"^\s*(?:english|ingilizce|i̇ngilizce)\s*:\s*$"
        if language == "tr"
        else r"^\s*(?:türkçe|turkce|turkish)\s*:\s*$",
        flags=re.IGNORECASE,
    )
    kept: list[str] = []
    for line in lines:
        if forbidden_heading.fullmatch(line.strip()):
            break
        kept.append(line)
    return "\n".join(kept).strip() or answer.strip()


def _trim_dangling_ending(answer: str) -> str:
    stripped = answer.strip()
    if not stripped:
        return ""
    if stripped.endswith((".", "!", "?", "]")):
        return stripped
    if stripped.endswith((":", "-", ";", "/")):
        return _trim_to_sentence(stripped[:-1]).strip()
    if len(stripped) > 160:
        trimmed = _trim_to_sentence(stripped).strip()
        return trimmed or stripped
    return stripped


def parse_grounded_status(text: str) -> tuple[str, str]:
    """Parse the optional GroundNote STATUS contract conservatively."""
    cleaned = text.replace("\r\n", "\n").replace("\r", "\n").strip()
    lines = cleaned.splitlines()
    if not lines:
        return "supported", cleaned
    first = lines[0].strip().casefold()
    if first == "status: supported":
        return "supported", "\n".join(lines[1:]).strip()
    if first == "status: insufficient":
        return "insufficient", "\n".join(lines[1:]).strip()
    return "supported", cleaned


def insufficient_evidence_text(language: str) -> str:
    """Return deterministic no-answer text in the resolved language."""
    if language == "tr":
        return (
            "Bu sorunun cevabı indekslenmiş belgelerde bulunamadı. "
            "Daha belirli bir soru sormayı veya ilgili başka bir belge eklemeyi deneyin."
        )
    return (
        "I could not find the answer in the indexed documents. "
        "Try refining the question or adding relevant documents."
    )


def repeating_generation_text(language: str) -> str:
    """Return deterministic repeated-generation failure text."""
    if language == "tr":
        return (
            "Yanıt oluşturulurken tekrar eden bir çıktı algılandı. Lütfen soruyu biraz daha "
            "daraltarak tekrar deneyin."
        )
    return (
        "A repeating generation was detected while creating the answer. Please try a narrower "
        "question."
    )


def indicates_insufficient_evidence(answer: str, *, language: str) -> bool:
    """Recognize an explicit model refusal and avoid presenting it as grounded."""
    normalized = " ".join(answer.casefold().split())
    if "status: insufficient" in normalized:
        return True
    english_markers = (
        "insufficient evidence",
        "not enough evidence",
        "do not contain enough evidence",
        "does not contain enough evidence",
        "does not contain specific information",
        "does not describe",
        "provided context is unrelated",
        "retrieved context is unrelated",
        "could not find the answer",
        "cannot find the answer",
        "answer was not found",
    )
    turkish_markers = (
        "yeterli kanıt yok",
        "yeterli bilgi yok",
        "yeterli kanıt bulunmuyor",
        "belgelerde bulunamadı",
        "cevaplamak için yeterli",
    )
    markers = turkish_markers if language == "tr" else english_markers
    return any(marker in normalized for marker in markers)


def _has_plausible_context_overlap(query: str, context_items: list[RagContextItem]) -> bool:
    query_terms = _content_terms(query)
    if not query_terms:
        return True
    context_terms = _normalize_terms("\n".join(item.content for item in context_items))
    overlap = query_terms & context_terms
    if overlap:
        return True
    if any(term.isdigit() and len(term) == 4 for term in query_terms):
        return False
    code_terms = {term for term in query_terms if re.fullmatch(r"[a-z]{1,4}\d{1,4}[a-z]?", term)}
    if code_terms:
        return bool(code_terms & context_terms)
    return True


def _misses_strong_entities(query: str, context_items: list[RagContextItem]) -> bool:
    strong_terms = _strong_query_entities(query)
    if len(strong_terms) < 2:
        return False
    context_terms = _normalize_terms(
        "\n".join(
            [
                *[item.content for item in context_items],
                *[item.section_title or "" for item in context_items],
                *[item.source_filename for item in context_items],
            ]
        )
    )
    missing = strong_terms - context_terms
    return len(missing) >= 2


def _strong_query_entities(query: str) -> set[str]:
    stopwords = {
        "about",
        "answer",
        "battery",
        "belge",
        "belgelerde",
        "capacity",
        "cevap",
        "documents",
        "fuel",
        "hakkinda",
        "hakkında",
        "hybrid",
        "icin",
        "için",
        "nedir",
        "nasil",
        "nasıl",
        "power",
        "question",
        "soru",
        "the",
        "what",
        "where",
        "which",
    }
    raw_terms = re.findall(
        r"[A-Za-zÇĞİÖŞÜçğıöşü0-9][A-Za-zÇĞİÖŞÜçğıöşü0-9.+-]*",
        query,
        flags=re.UNICODE,
    )
    strong: set[str] = set()
    for raw in raw_terms:
        folded = next(iter(_normalize_terms(raw)), "")
        if not folded or folded in stopwords:
            continue
        if len(folded) >= 3 and (
            raw[:1].isupper() or any(character.isdigit() for character in raw) or "." in raw
        ):
            strong.add(folded)
    return strong


def _requests_bilingual_answer(query: str) -> bool:
    normalized = " ".join(_normalize_terms(query))
    return (
        "english" in normalized
        and ("turkce" in normalized or "turkish" in normalized)
        or "ingilizce" in normalized
        and "turkce" in normalized
    )


def _content_terms(text: str) -> set[str]:
    stopwords = {
        "about",
        "according",
        "belge",
        "belgede",
        "belgelerde",
        "buna",
        "does",
        "gore",
        "göre",
        "hakkinda",
        "hakkında",
        "how",
        "icin",
        "için",
        "nedir",
        "nasil",
        "nasıl",
        "ne",
        "the",
        "what",
        "when",
        "where",
    }
    return {term for term in _normalize_terms(text) if len(term) >= 3 and term not in stopwords}


def _normalize_terms(text: str) -> set[str]:
    normalized = (
        text.casefold()
        .replace("ı", "i")
        .replace("ş", "s")
        .replace("ğ", "g")
        .replace("ü", "u")
        .replace("ö", "o")
        .replace("ç", "c")
    )
    terms = {
        term.strip(".-") for term in re.findall(r"[a-z0-9.-]+", normalized, flags=re.IGNORECASE)
    }
    terms.discard("")
    expanded = set(terms)
    for term in terms:
        for suffix in (
            "lari",
            "leri",
            "lar",
            "ler",
            "nin",
            "dan",
            "den",
            "dir",
            "dur",
            "tir",
            "tur",
            "i",
            "u",
        ):
            if term.endswith(suffix) and len(term) > len(suffix) + 2:
                expanded.add(term[: -len(suffix)])
    return expanded


def safe_performance_report(answer: RagAnswer) -> dict[str, object]:
    """Return safe answer timing metadata without prompts, queries, documents, or vectors."""
    return {
        "duration_ms": answer.duration_ms,
        "grounded": answer.grounded,
        "insufficient_evidence": answer.insufficient_evidence,
        "retrieved_count": answer.retrieved_count,
        "used_context_count": answer.used_context_count,
        "citation_count": len(answer.citations),
        "model": answer.model,
        "warnings": list(answer.warnings),
    }


def _top_score(retrieval: RetrievalResponse) -> float:
    if not retrieval.results:
        return -1.0
    return max(result.score for result in retrieval.results)


def _first_repetition_start(text: str) -> int | None:
    tokens = list(re.finditer(r"\b[\w'-]+\b|\[[sS]\d+\]", text, flags=re.UNICODE))
    if len(tokens) < 3:
        return None
    lowered = [token.group(0).casefold() for token in tokens]
    for index in range(len(lowered) - 2):
        if lowered[index] == lowered[index + 1] == lowered[index + 2]:
            return tokens[index].start()
    for size in range(2, 6):
        window = size * 3
        if len(lowered) < window:
            continue
        for index in range(0, len(lowered) - window + 1):
            phrase = lowered[index : index + size]
            if (
                phrase
                == lowered[index + size : index + 2 * size]
                == lowered[index + 2 * size : index + 3 * size]
            ):
                return tokens[index].start()
    tail = lowered[-24:]
    if len(tail) >= 12 and len(set(tail)) <= 3:
        return tokens[max(0, len(tokens) - 24)].start()
    return None


def _trim_to_sentence(text: str) -> str:
    stripped = text.rstrip()
    if stripped.endswith("]") and CITATION_RE.search(stripped):
        return stripped
    sentence_ends = [stripped.rfind(mark) for mark in (".", "!", "?", "。", "؟")]
    end = max(sentence_ends)
    if end >= 40:
        return stripped[: end + 1]
    lines = [line for line in stripped.splitlines() if line.strip()]
    while lines and not lines[-1].strip().endswith((".", "!", "?", "]")):
        lines.pop()
    return "\n".join(lines)


def _collapse_duplicate_citations(answer: str, *, allowed_ids: set[str]) -> str:
    seen: set[str] = set()

    def replace(match: re.Match[str]) -> str:
        citation_id = match.group(1)
        if citation_id not in allowed_ids:
            return ""
        if citation_id in seen:
            return ""
        seen.add(citation_id)
        return f"[{citation_id}]"

    cleaned = re.sub(r"\[([sS]\d+)\]", replace, answer)
    return re.sub(r"[ \t]{2,}", " ", cleaned).strip()
