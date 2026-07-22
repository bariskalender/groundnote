# GroundNote Roadmap

| Phase | Name | Status |
| --- | --- | --- |
| 0 | Repository foundation and application shell | Complete |
| 1 | Environment verification and Foundry Local discovery | Complete |
| 2 | Configuration, Domain Models, and SQLite Storage | Complete |
| 3 | Secure document validation and parsing | Complete |
| 4 | Hybrid Recursive Chunking and Pre-Embedding Ingestion | Complete |
| 5 | Embedding, Indexing, and Semantic Retrieval | Complete |
| 6 | Foundry Local chat provider and RAG answer generation | Complete |
| Audit | Pre-Phase 7 UI readiness audit | Complete |
| 7 | Streamlit Upload, Indexing, and Chat Interface | Complete |
| 7.1 | Product Stabilization, Retrieval Reliability, Performance, and Chat UX Rebuild | Complete |
| 7.1.1 | Automatic Document Processing, Simplified UI, and Windows Error Recovery | Complete |
| 7.2 | Performance, Answer Quality, Router Robustness, and Indexing Optimization | Complete |
| 7.2.1 | Real Test Stability, Resource Control, and Document Management Patch | Complete |
| 7.2.2 | Section Retrieval, Answer Completion, and UI State Fixes | Complete |
| 8 | Knowledge Base Management, Delete, Re-index, and Index Controls | Complete |
| 8.1 | Knowledge Base UI and Operation State Stabilization | Complete |
| 9 | Packaging and Release Preparation | Complete |
| 9.1A | RAG Correctness, Index Recovery, and Managed File Safety | Complete |
| 9.1B | Model Lifecycle and Indexing Performance | Complete |
| 9.1C | Multi-file Upload | Not started |
| 9.1D | Security and Release Hardening | Not started |

## Phase 9.1B Acceptance Notes

- Added a shared lifecycle that permits at most one GroundNote-owned chat provider to remain active
  across Fast and Balanced mode switches, with explicit failure rollback and shutdown cleanup.
- Completed embedding cleanup across indexing, retrieval, storage/FTS failure, interruption, and
  chat handoff paths without unloading models owned by another application.
- Added safe indexing stage timings, real unit progress, bounded process resource measurements,
  isolated benchmarking, and debug-only diagnostics.
- Removed repeated upload-byte reads and file hashing while preserving duplicate detection before
  embedding; verified one parse, one chunking pass, ordered batches, and transactional failures.
- Retained synchronous sequential indexing and blocked chat during indexing based on measured CPU
  contention; background queues remain deferred.
- Phase 9.1C multi-file upload remains next and unstarted. Phase 9.1D security/release hardening is
  also unstarted.

## Phase 9.1A Acceptance Notes

- Removed topic-specific deterministic factual answers; factual document questions now require
  relevant retrieved evidence and the normal citation validation path.
- Added a centralized Ready integrity contract covering committed chunks, compatible float32
  embeddings, document model metadata, and one valid FTS row per chunk.
- Added idempotent bootstrap recovery for interrupted transient states and incomplete Ready records;
  affected documents become non-searchable and immediately retryable.
- Added final indexing integrity validation and failure cleanup so partial embeddings or FTS rows
  cannot become usable or cited.
- Remove and clear-all now delete only validated GroundNote-managed copies represented by database
  records; original selected files and unrelated managed-directory files remain untouched.
- Phase 9.1B performance/resource work is complete; Phase 9.1C multi-file upload and Phase 9.1D
  security/release hardening remain deferred.

## Phase 9 Acceptance Notes

- Added GroundNote `0.9.0` as single-source package metadata exposed through
  `importlib.metadata`.
- Added idempotent Windows setup, privacy-safe doctor, localhost launcher, and PID/token-scoped
  stop workflows without automatic model downloads or broad process termination.
- Added a deterministic portable source ZIP builder that excludes local data, documents,
  databases, logs, models, caches, secrets, tests, and generated artifacts.
- Documented the portable ZIP as the recommended release direction; native installers remain
  deferred until clean-machine, signing, antivirus, upgrade, and licensing checks are complete.
- Preserved existing RAG, Knowledge Base, session, privacy, and local model behavior.

## Phase 8 Acceptance Notes

- Added a localized Knowledge Base with safe document metadata and indexing statuses.
- Added confirmed per-document removal, clear-all local-index removal, and sequential per-document
  re-indexing without deleting original source files.
- Added operation-safe New chat behavior and clearer empty-chat guidance without persistent chat
  history.
- Preserved local-only processing, source filtering, Phase 7.2.2 retrieval behavior, and
  hidden-by-default technical details.
- Re-index all and background indexing remain deliberately deferred.

## Phase 0 Acceptance Notes

- Create the repository structure and required governance documents.
- Configure Python packaging, dependencies, Ruff, mypy, and pytest.
- Add a minimal Streamlit app shell.
- Do not implement document parsing, embeddings, retrieval, Foundry Local integration, or RAG.

## Phase 1 Acceptance Notes

- Foundry Local CLI status is known and documented.
- Foundry Local SDK initializes and lists the current model catalog.
- Provider interfaces and Foundry-backed provider wrappers exist.
- Fake providers support normal unit tests without model downloads.
- Lightweight chat and embedding candidates were benchmarked sequentially.
- No document ingestion, SQLite storage, retrieval, or Streamlit chat was implemented.

## Phase 2 Acceptance Notes

- Typed settings load from defaults, `.env`, and `GROUNDNOTE_` environment variables.
- Structured logging is configured explicitly and redacts sensitive fields.
- Domain models exist for documents, chunks, retrieval results, and answers.
- SQLite migrations create `documents`, `document_chunks`, and `application_metadata`.
- Embeddings serialize as finite one-dimensional float32 BLOB values.
- Document and vector repositories work through a transaction-aware Unit of Work.
- Bootstrap initializes settings, logging, directories, and database schema.
- No parsing, ingestion, retrieval, RAG generation, or Streamlit chat was implemented.

## Phase 3 Acceptance Notes

- Secure validation works for PDF, DOCX, TXT, and Markdown file extensions.
- Safe stored filenames are generated with UUID prefixes and traversal protection.
- SHA-256 hashes are calculated from original file bytes using streaming reads.
- Exact duplicate pre-checks use the existing document repository before parsing.
- PDF text extraction preserves 1-based page numbers and reports blank/scanned-page limitations.
- DOCX extraction preserves headings, paragraphs, lists, and simple table text with null page
  numbers.
- TXT supports UTF-8 and UTF-8 with BOM while rejecting binary-looking text files.
- Markdown headings, lists, code blocks, Unicode, and inert HTML text are preserved.
- Parser registry and document processing service are independent of Streamlit and Foundry Local.
- No chunking, embedding generation, indexing, semantic retrieval, RAG generation, or final chat UI
  was implemented.

## Phase 4 Acceptance Notes

- Added deterministic hybrid recursive chunking with paragraph, sentence, whitespace, and hard
  split fallbacks.
- Preserved page numbers, section titles, source order metadata, chunk indexes, chunking version,
  and approximate token estimates.
- Added overlap only between compatible chunks and avoided overlap across PDF pages or unrelated
  headings.
- Added safe short-fragment merging with warnings when boundaries prevent a safe merge.
- Added transaction-safe pre-embedding ingestion for PDF, DOCX, TXT, and Markdown.
- Persisted document metadata and chunks with `PENDING_EMBEDDING` status and null embedding fields.
- No embeddings, Foundry model calls, semantic retrieval, RAG generation, or final upload/chat UI
  were implemented.

## Phase 5 Acceptance Notes

- Added local embedding validation, normalization, and batch generation through Foundry Local.
- Stored normalized float32 embeddings and embedding metadata in SQLite.
- Added transaction-safe document indexing with `PENDING_EMBEDDING -> INDEXING -> INDEXED` status
  flow.
- Added safe force re-indexing and embedding clearing foundations.
- Added NumPy cosine-similarity semantic retrieval with top-k, candidate limits, minimum score, and
  document/file/page filters.
- Returned ranked chunks with filename, file type, page, section, source order, score, and metadata.
- No chat model calls, RAG answer generation, final upload/chat UI, external vector database, or
  cloud API were implemented.

## Phase 6 Acceptance Notes

- Added grounded single-turn RAG answer generation using retrieved chunks and Foundry Local chat.
- Added RAG query validation, Turkish/English response-language handling, bounded context assembly,
  citation IDs, citation validation, and deterministic insufficient-evidence responses.
- Added prompt-injection defenses that keep retrieved document text out of system instructions and
  treat source content as untrusted evidence.
- Added local-only chat provider fallback through the loopback Foundry daemon for preview SDK
  runtime issues.
- Added RAG unit, integration, privacy, citation, prompt-safety, and fake-provider pipeline tests.
- Added RAG generation, prompt-safety, and citations/language documentation.
- No final Streamlit chat UI, persistent conversation memory, cloud API, external vector database,
  or Phase 7 work was implemented.

## Pre-Phase 7 UI Readiness Audit Notes

- Verified the Phases 0-6 backend foundation before Streamlit upload, indexing, Knowledge Base,
  and chat UI work.
- Fixed indexing transaction duration so local embedding model loading and generation no longer
  hold a SQLite write transaction open.
- Confirmed startup remains lightweight and does not load chat or embedding models.
- Confirmed uploaded-file helpers, document validation, duplicate detection, parsing, chunking,
  indexing, retrieval, RAG generation, citations, privacy protections, and logging are ready for a
  Phase 7 UI adapter.
- Added `docs/audits/pre-phase-7-ui-readiness-audit.md`.
- At audit completion, Phase 7 had not started.

## Phase 7 Acceptance Notes

- Added a wide Streamlit application with Documents and Ask GroundNote navigation.
- Added explicit one-file upload confirmation for PDF, DOCX, TXT, and Markdown with aligned 50 MB
  Streamlit and backend limits.
- Connected safe uploaded-byte writing, duplicate detection, ingestion, chunking, persistence, local
  embedding indexing, document status, RAG answers, and trusted citations through high-level
  workflows.
- Added indexed-document and file-type source filters without UI SQL or direct provider calls.
- Added deterministic safe error mapping, duplicate presentation, insufficient-evidence behavior,
  and local-model lifecycle feedback.
- Added controlled session state containing only safe latest-result data; no persistent or
  history-aware chat was added.
- Verified fake-provider and real Foundry Local UI-backend flows, Streamlit application behavior,
  rerun safety, duplicate handling, and model cleanup.
- Added `docs/streamlit-interface.md` and `docs/demo-workflow.md`.
- No deletion UI, re-index UI, full Knowledge Base management, OCR, cloud inference, or Phase 8
  work was implemented.

## Phase 7.1 Acceptance Notes

- Removed pre-scoring SQL candidate starvation so long documents and later documents remain
  searchable before final ranking limits are applied.
- Added SQLite FTS5 lexical search with hybrid ranking, heading and numbered-term boosts,
  conservative typo expansion, and adjacent-context support.
- Added deterministic routing for greetings, thanks, and app help so simple messages bypass
  retrieval and local model loading.
- Added a stronger supported/insufficient generation contract with citation-free insufficient
  evidence.
- Changed the default model lifecycle to keep models warm during an interactive session while
  preserving Memory saver and manual unload behavior.
- Rebuilt Streamlit around a chat-first main view with sidebar upload, source filters, performance
  mode, Turkish/English UI text, session-only chat history, New chat, compact citations, and
  recoverable operation state.
- Added multiple-file upload and minimal retry indexing without implementing Phase 8 Knowledge Base
  management.

## Phase 7.1.1 Acceptance Notes

- Replaced cached stdout-bound Structlog logging with idempotent standard-library integration and a
  UTF-8 local file handler that does not retain Windows file handles between records.
- Prevented logging failures from masking original application failures and disabled detailed
  Streamlit browser exceptions.
- Removed the manual Process documents action and permanent indexing administration panels.
- Added automatic local, synchronous, sequential processing after file selection with stable
  rerun-safe upload identities, duplicate skipping, per-file failure isolation, and byte cleanup.
- Added a compact document list with safe statuses and inline retry for failed documents.
- Moved session settings and model unloading behind the upper-right gear popover.
- Verified multiple uploads, corrupt-file recovery, duplicates, grounded chat, settings reruns, New
  chat document preservation, and model cleanup on Windows without starting Phase 8.

## Phase 7.2 Acceptance Notes

- Added deterministic handling for empty, unclear, greeting, thanks, and help inputs before
  retrieval or local model calls.
- Allowed short automotive and technical terms such as `W123`, `NVH`, `CRC`, `VIN`, and `API` to
  continue through document retrieval.
- Added no-ready-document and processing-document responses without loading models.
- Tightened the RAG prompt to `grounded-rag-v2` with compact citations, natural Turkish guidance,
  repetition avoidance, and clearer chassis/body-code versus engine-code separation.
- Added repeated-word, repeated-phrase, repeated-citation, and low-diversity-tail output repair with
  one stricter regeneration attempt.
- Reduced default RAG context and output budgets and skipped chat generation for low-confidence
  retrieval.
- Kept embedding providers warm inside a session unless Memory saver or manual unload releases
  them.
- Removed normal-flow technical citation details and kept compact trusted source labels.
- Improved image-only PDF/OCR-safe messaging without adding OCR or hallucinated summaries.
- Added `docs/phase-7-2-optimization.md`.

## Phase 7.2.1 Acceptance Notes

- Added minimal confirmed single-document removal from the Streamlit document list without deleting
  user source files from disk.
- Added metadata-based document inventory/grouping answers that skip retrieval and chat generation.
- Added a disabled-by-default debug details toggle while keeping normal sources visible.
- Added UI operation guards and sequential upload behavior so indexing and answer generation are not
  started together.
- Added modest performance-mode model idle cleanup and unloaded chat models before indexing.
- Strengthened concise answer prompting, answer cleanup, bilingual guidance, and table/numeric
  caution.
- Added regression tests for document deletion, inventory routing, debug-detail default visibility,
  and MB-like table ambiguity.
- Added `docs/phase-7-2-1-real-test-stability.md`.

## Phase 7.2.2 Acceptance Notes

- Added section-title-aware RAG context filtering for specific named items and sections while
  preserving explicit comparisons.
- Added a strong-entity unsupported-question shortcut that returns insufficient evidence without
  chat generation when retrieved chunks do not contain the named entities.
- Hardened generated-answer formatting cleanup for empty bullets, citation-only bullets, duplicate
  answer headings, unrequested bilingual tails, dangling endings, and malformed-output markers.
- Updated deterministic language routing so Turkish greetings remain Turkish without requiring
  Turkish-only characters.
- Changed overlapping Streamlit question attempts to show a friendly busy message instead of a
  generic operation failure.
- Shortened the single-document remove confirmation wording and kept Phase 8 management features
  out of scope.
- Added `docs/phase-7-2-2-section-retrieval-ui-stability.md`.
