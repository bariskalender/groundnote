# Project State

## Current Phase

Phase 7.2 complete locally. Phase 8 has not started.

## Completed Tasks

### Phase 0

- Created the src-layout repository structure.
- Added governance documents, dependency configuration, quality tooling, and a minimal
  Streamlit application shell.
- Added a smoke test that imports the package.

### Phase 1

- Installed and verified Microsoft Foundry Local CLI `0.10.2`.
- Installed and verified `foundry-local-sdk-winml` `1.2.3`.
- Added provider-neutral chat and embedding interfaces.
- Added Foundry Local chat and embedding provider wrappers.
- Benchmarked `phi-3.5-mini`, `qwen2.5-0.5b`, and `qwen3-embedding-0.6b`.

### Phase 2

- Added typed settings with `pydantic-settings` and `platformdirs`.
- Added explicit directory initialization without import-time filesystem writes.
- Added privacy-aware structured logging helpers.
- Added domain models for documents, chunks, retrieval results, and answers.
- Added SQLite connection management with foreign keys, row factory, and busy timeout.
- Added versioned migration runner and `001_initial.sql`.
- Added `documents`, `document_chunks`, `application_metadata`, and `schema_migrations` tables.
- Added float32 embedding BLOB serialization and deserialization utilities.
- Added document and vector repository interfaces and SQLite implementations.
- Added lightweight SQLite Unit of Work with explicit commit and rollback behavior.
- Added application bootstrap for settings, logging, directory creation, and migrations.
- Updated the minimal Streamlit shell to run safe bootstrap and show initialization status.
- Added configuration and database schema documentation.

### Phase 3

- Added secure validation for PDF, DOCX, TXT, and Markdown files.
- Added safe display filename normalization and UUID-prefixed stored filename generation.
- Added streaming SHA-256 hashing for original file bytes.
- Added exact duplicate pre-checking through the existing document repository contract.
- Added parser-neutral `ParsedDocument`, `ParsedSection`, `ValidationResult`, and
  `DuplicateCheckResult` models.
- Added PDF parsing with page-by-page extraction, 1-based page numbers, blank-page warnings,
  encrypted PDF rejection, corrupted PDF rejection, and scanned/image-only limitations.
- Added DOCX parsing for headings, paragraphs, list text, and simple table text.
- Added TXT parsing for UTF-8 and UTF-8 with BOM with binary-looking file rejection.
- Added Markdown parsing with heading sections, lists, code blocks, Unicode, and inert HTML text.
- Added a parser registry and document processing service.
- Added safe uploaded-byte writing helper for future UI integration.
- Added supported-document and document-processing documentation.

### Phase 4

- Added a dedicated `groundnote.chunking` package with provider-neutral contracts and models.
- Added validated chunking settings with `hybrid-recursive-v1` as the MVP default version.
- Added deterministic hybrid recursive chunking with paragraph, sentence, whitespace, and hard
  character fallbacks.
- Added lightweight English and Turkish sentence splitting heuristics without NLP dependencies.
- Added overlap between compatible chunks while avoiding PDF page and unrelated heading crossings.
- Added safe short-fragment merging and warnings for unavoidable undersized chunks.
- Added source filename, file type, page, heading, source order, chunking version, warnings, and
  approximate token metadata.
- Added transaction-safe pre-embedding ingestion that persists document records and chunk rows with
  null embedding fields.
- Added a SQLite migration for chunk source metadata.
- Added chunking and pre-embedding ingestion documentation.

### Phase 5

- Added embedding configuration for model, dimension, dtype, batch size, version, top-k, candidate
  limit, and minimum score.
- Added normalized float32 embedding validation and embedding service wrappers.
- Added SQLite embedding metadata migration for document and chunk rows.
- Extended vector repository behavior for saving, clearing, loading, filtering, and counting
  indexed embeddings.
- Added transaction-safe document indexing and force re-index foundations.
- Added NumPy cosine-similarity semantic retrieval with deterministic ranking.
- Added document ID, file type, page number, score threshold, top-k, and candidate limit filters.
- Added retrieval results with filename, file type, page, section, source order, score, and safe
  metadata.
- Fixed Foundry Local manager reuse for the installed preview SDK singleton behavior.
- Added embedding/indexing and semantic retrieval documentation.

### Phase 6

- Added a dedicated `groundnote.rag` package for single-turn grounded answer generation.
- Added typed RAG settings for retrieval limits, context limits, generation limits, prompt version,
  citation requirements, and maximum query length.
- Connected semantic retrieval to local Foundry chat generation through provider interfaces.
- Added bounded context selection with stable citation IDs such as `S1`, `S2`, and `S3`.
- Added prompt-injection defenses with separated system/user prompts and explicitly delimited
  untrusted retrieved context.
- Added citation formatting and validation based only on trusted retrieval metadata.
- Added deterministic insufficient-evidence responses in Turkish and English.
- Added Turkish and English response-language handling with explicit override support.
- Added a loopback-only local Foundry daemon fallback for chat model loading when direct preview SDK
  loading fails.
- Added RAG unit, integration, privacy, prompt-safety, citation, and fake-provider pipeline tests.
- Added RAG generation, prompt-safety, and citations/language documentation.

### Pre-Phase 7 UI Readiness Audit

- Audited application composition, Streamlit rerun readiness, service boundaries, error behavior,
  upload lifecycle, document processing, indexing, retrieval, RAG generation, citations, privacy,
  logging, SQLite concurrency, settings, dependencies, and security posture.
- Added `docs/audits/pre-phase-7-ui-readiness-audit.md`.
- Fixed indexing transaction duration so local embedding model loading and generation run outside
  SQLite write transactions.
- Added a regression test proving a separate SQLite write can complete while fake embedding
  generation is running.
- Updated indexing documentation to describe the short-transaction strategy and `FAILED` indexing
  behavior.

### Phase 7

- Replaced the minimal shell with a wide Streamlit application containing Documents and Ask
  GroundNote views.
- Added an explicit application context for settings, database factories, Foundry providers,
  ingestion, indexing, retrieval, RAG, status checking, and UI workflows without startup model
  loading.
- Added one-file PDF, DOCX, TXT, and Markdown upload confirmation with aligned 50 MB Streamlit and
  backend limits.
- Added safe local uploaded-byte writing, exact duplicate presentation and cleanup, parsing,
  chunking, persistence, local embedding indexing, and safe success summaries.
- Ensured the persisted stored filename matches the actual collision-resistant local upload file.
- Added user-safe document status summaries and read-only refresh behavior.
- Added indexed-document and file-type filters, single-turn chat input, grounded Markdown answers,
  trusted structured citations, and insufficient-evidence notices.
- Added a conservative conversion from explicit model evidence refusals to deterministic
  citation-free insufficient-evidence answers.
- Added controlled Streamlit session state without bytes, vectors, model instances, connections,
  transactions, or persistent conversation history.
- Added safe Foundry service status reporting without automatic service start, model loading, or
  download.
- Made model unload failures warning-only after successful embedding or chat operations so cleanup
  issues do not corrupt indexed state or valid answers.
- Added UI unit, integration, Streamlit AppTest, fake-provider pipeline, and real local Foundry smoke
  coverage.
- Added Streamlit interface and demonstration workflow documentation.

### Phase 7.1

- Fixed retrieval starvation by removing the pre-scoring SQL candidate limit.
- Added SQLite FTS5 lexical search, hybrid ranking, heading/numbered-term boosts, conservative
  typo-tolerant expansion, and adjacent-context support.
- Added deterministic greeting, thanks, and app-help routing that bypasses retrieval and model
  loading.
- Added a supported/insufficient RAG response contract and stronger citation-free insufficient
  evidence handling.
- Changed the interactive default to warm local models after first use, with Fast and Memory saver
  performance modes and manual model unload.
- Rebuilt Streamlit into a chat-first interface with sidebar upload, source filters, Turkish and
  English UI text, multiple-file upload, New chat, session-only history, compact citations, and
  recoverable operation state.
- Added `docs/phase-7-1-stabilization.md`.

### Phase 7.1.1

- Replaced cached stdout-bound Structlog logging with idempotent standard-library integration and
  best-effort failure-path logging that preserves the original exception.
- Added a UTF-8 rotating local log handler that closes the file after every record, preventing stale
  Streamlit streams and Windows file locks.
- Disabled detailed Streamlit browser exceptions and expanded localized safe error mapping.
- Removed the manual document-processing button and permanent indexing administration panels.
- Added automatic sequential upload processing with stable identities, rerun protection, duplicate
  skipping, per-file failure isolation, and no uploaded bytes in session state.
- Added compact document statuses and inline retry that safely reuses persisted document and chunk
  identities when possible.
- Moved language, performance, answer-language, and model lifecycle controls into an upper-right
  gear popover.
- Hardened operation state with IDs, timestamps, terminal status, stale recovery, and `try/finally`
  cleanup.
- Added Windows logging, automatic upload, corrupt-file continuation, UI state, and Streamlit
  AppTest regressions.
- Updated the Streamlit, indexing, demonstration, stabilization, README, roadmap, state, and
  decision documentation.

### Phase 7.2

- Added deterministic router handling for empty, unclear, greeting, thanks, help, no-document, and
  processing-document states before retrieval or model calls.
- Kept short automotive and technical terms such as `W123`, `NVH`, `CRC`, `VIN`, and `API`
  eligible for retrieval.
- Tightened the grounded RAG prompt to `grounded-rag-v2` with compact citations, natural Turkish
  guidance, repetition avoidance, and chassis/body-code versus engine-code separation.
- Added repeated-word, repeated-phrase, repeated-citation, low-diversity-tail, and excessive-length
  answer protection with local trimming and one stricter regeneration attempt.
- Added deterministic low-confidence retrieval shortcut that skips chat generation and returns
  insufficient evidence.
- Reduced default local RAG context/output budgets for latency.
- Added loaded-state tracking in `EmbeddingService` so warm sessions do not repeatedly load the
  embedding provider for sequential uploads and retrieval bursts.
- Removed normal-flow technical citation details and kept compact trusted source labels.
- Improved image-only PDF/OCR limitation messaging without adding OCR.
- Added `docs/phase-7-2-optimization.md`.

## Commands Run In Phase 2

- `uv sync`
- `uv run ruff check .`
- `uv run ruff check . --fix`
- `uv run ruff format --check .`
- `uv run mypy src`
- `uv run pytest -m "not foundry"`
- `uv run pytest --cov=groundnote --cov-report=term-missing`
- `uv run streamlit run src/groundnote/app.py`

## Commands Run In Phase 3

- `uv sync`
- `uv run pytest tests/unit/documents tests/integration/documents`
- `uv run ruff check .`
- `uv run ruff format --check .`
- `uv run mypy src`
- `uv run pytest -m "not foundry"`
- `uv run pytest --cov=groundnote --cov-report=term-missing`
- `uv run python scripts/check_foundry.py`
- `uv run streamlit run src/groundnote/app.py`

## Commands Run In Phase 4

- `uv sync`
- `uv run ruff check .`
- `uv run ruff format --check .`
- `uv run mypy src`
- `uv run pytest tests/unit/chunking tests/integration/ingestion -q --basetemp .local-data/pytest-phase4-target`
- `uv run pytest -m "not foundry" --basetemp .local-data/pytest-phase4-full`
- `uv run pytest --cov=groundnote --cov-report=term-missing --basetemp .local-data/pytest-phase4-cov`
- `uv run python scripts/check_foundry.py`
- `foundry status`
- Targeted chunking and pre-embedding ingestion smoke test.
- Headless Streamlit startup smoke test.

## Commands Run In Phase 5

- `foundry server status`
- `foundry status`
- `foundry model download qwen3-embedding-0.6b`
- `uv sync`
- `uv run ruff check .`
- `uv run ruff format --check .`
- `uv run mypy src`
- `uv run pytest tests/unit/embeddings tests/unit/retrieval tests/integration/indexing -q --basetemp .local-data/pytest-phase5-target`
- `uv run pytest -m "not foundry" --basetemp .local-data/pytest-phase5-full`
- `uv run pytest --cov=groundnote --cov-report=term-missing --basetemp .local-data/pytest-phase5-cov`
- `uv run python scripts/check_foundry.py`
- Real Foundry embedding smoke test with `qwen3-embedding-0.6b`.
- Real end-to-end ingestion, indexing, and retrieval smoke test.
- Headless Streamlit startup smoke test.

## Commands Run In Phase 6

- `git status`
- `git status -sb`
- `git branch --show-current`
- `git remote -v`
- `git log -6 --oneline`
- `git log origin/main..HEAD --oneline`
- `git diff origin/main..HEAD --stat`
- `git ls-files`
- `foundry server status`
- `foundry server start`
- `foundry status`
- `foundry model download qwen2.5-0.5b-instruct-generic-cpu:4`
- `foundry model download Phi-3.5-mini-instruct-generic-cpu:2`
- `uv sync`
- `uv run ruff check .`
- `uv run ruff format --check .`
- `uv run mypy src`
- `uv run pytest -m "not foundry" --basetemp .local-data/pytest-phase6-full1`
- `uv run pytest --cov=groundnote --cov-report=term-missing --basetemp .local-data/pytest-phase6-cov1`
- `uv run python scripts/check_foundry.py`
- Targeted RAG unit and integration tests.
- Real Foundry chat smoke test.
- Real local end-to-end RAG smoke test.
- Headless Streamlit startup smoke test.

## Commands Run In Pre-Phase 7 UI Readiness Audit

- `git status`
- `git status -sb`
- `git branch --show-current`
- `git remote -v`
- `git log -8 --oneline`
- `git fetch origin`
- `git log HEAD..origin/main --oneline`
- `git log origin/main..HEAD --oneline`
- `git ls-files`
- Security and privacy source searches with `rg`.
- `uv run pytest tests/integration/indexing/test_indexing_and_retrieval.py -q --basetemp .local-data/pytest-prephase7-indexing`
- Fake-provider UI-backend pipeline timing smoke test.
- `uv sync`
- `uv run ruff check .`
- `uv run ruff format --check .`
- `uv run mypy src`
- `uv run pytest -m "not foundry" --basetemp .local-data/pytest-prephase7-full`
- `uv run python scripts/check_foundry.py`
- Real local end-to-end RAG smoke test with cached Foundry Local embedding and chat models.
- `foundry status`
- Final `uv run ruff check .`, `uv run mypy src`, and
  `uv run pytest -m "not foundry" --basetemp .local-data/pytest-prephase7-final`

## Commands Run In Phase 7

- Initial Git status, branch, remote, fetch, synchronization, history, and tracked-file checks.
- `uv sync`
- `uv run ruff check .`
- `uv run ruff format --check .`
- `uv run mypy src`
- Targeted UI unit, integration, Streamlit AppTest, RAG evidence, and model-lifecycle tests.
- `uv run pytest -m "not foundry" --basetemp .local-data/pytest-phase7-final`
- `uv run pytest --cov=groundnote --cov-report=term-missing --basetemp .local-data/pytest-phase7-cov-final`
- `uv run python scripts/smoke_ui_pipeline.py`
- `foundry --version`
- `foundry server status`
- `foundry status`
- `uv run python scripts/check_foundry.py`
- `uv run python scripts/smoke_ui_real.py`
- `uv run streamlit run src/groundnote/app.py --server.headless true --server.port 8507`
- Manual in-app browser smoke for upload, indexing, Ready status, grounded answer, citation,
  insufficient evidence, duplicate handling, rerun behavior, and safe console output.
- Security and privacy source/tracked-file searches with `rg` and Git.

## Commands Run In Phase 7.1

- Initial Git status, branch, remote, fetch, synchronization, history, and tracked-file checks.
- `uv run ruff check src tests`
- `uv run mypy src`
- Targeted retrieval, RAG, UI state, migration, UI workflow, and AppTest checks.
- `uv run pytest -m "not foundry" --basetemp .local-data/pytest-phase71-full1`
- `uv sync`
- `uv run ruff check .`
- `uv run ruff format src\groundnote\app.py src\groundnote\retrieval\service.py`
- `uv run ruff format --check .`
- `uv run mypy src`
- `uv run pytest -m "not foundry" --basetemp .local-data/pytest-phase71-full-final`
- `uv run pytest -m "not foundry" --basetemp .local-data/pytest-phase71-full-postfix`
- `uv run pytest --cov=groundnote --cov-report=term-missing --basetemp .local-data/pytest-phase71-cov-final`
- `uv run python scripts/check_foundry.py`
- `foundry status`
- `uv run python scripts/smoke_ui_pipeline.py`
- `uv run python scripts/smoke_ui_real.py`
- `uv run streamlit run src/groundnote/app.py --server.headless=true --server.port=8509`
- Manual in-app browser smoke for chat-first layout, sidebar controls, multiple-file uploader,
  bottom chat input, and greeting submission.
- `foundry model unload Phi-3.5-mini-instruct-generic-cpu:2`
- `foundry model unload qwen3-embedding-0.6b-generic-cpu:1`
- Deterministic greeting workflow timing smoke.

## Commands Run In Phase 7.1.1

- Initial Git branch, cleanliness, remote, synchronization, history, and Phase 8 safety checks.
- `uv sync`
- `uv run ruff check .`
- `uv run ruff format --check .`
- `uv run mypy src`
- Targeted logging, upload, UI state, workflow, pipeline, and Streamlit AppTest checks.
- `uv run pytest -m "not foundry" --basetemp .local-data/pytest-phase711-postreview-final`
- `uv run pytest --cov=groundnote --cov-report=term-missing --basetemp .local-data/pytest-phase711-coverage-postreview`
- `uv run python scripts/check_foundry.py`
- `uv run python scripts/smoke_ui_pipeline.py`
- `uv run python scripts/smoke_ui_real.py`
- `uv run streamlit run src/groundnote/app.py --server.headless=true --server.port=8511`
- Manual in-app Windows browser smoke for automatic DOCX/PDF upload, corrupt-file continuation,
  inline retry, duplicates, settings reruns, grounded follow-up chat, New chat, and model unloading.
- `foundry status`
- Security, privacy, generated-file, and tracked-file searches with `rg` and Git.

## Commands Run In Phase 7.2

- Initial Git branch, cleanliness, remote, synchronization, history, and Phase 8 safety checks.
- Security and tracked-file checks with `rg` and Git.
- Targeted router, RAG repetition, citation cleanup, UI workflow, and safe error tests.
- `uv run ruff check src tests`
- `uv run ruff format src\groundnote\rag\service.py`
- `uv sync`
- `uv run ruff check .`
- `uv run ruff format --check .`
- `uv run mypy src`
- `uv run pytest -m "not foundry" --basetemp .local-data/pytest-phase72-full-final5`
- `uv run pytest --cov=groundnote --cov-report=term-missing --basetemp .local-data/pytest-phase72-cov-final`
- `uv run python scripts/check_foundry.py`
- `uv run python scripts/smoke_ui_pipeline.py`
- `uv run python scripts/smoke_ui_real.py`
- Headless Streamlit startup smoke on port 8512.
- Manual Windows real-document timing smoke with MB nomenclature PDF, Turkish design PDF, generated
  image-only PDF, and a small TXT fixture.

## Test Status

- Phase 7 UI unit/integration/Streamlit target: Passed.
- Phase 7 fake-provider UI pipeline: Passed with one indexed chunk, one trusted citation,
  insufficient evidence, duplicate detection, persistence after context restart, and no chat
  history.
- Phase 7 real Foundry UI-backend smoke: Passed with 1024-dimensional local embeddings, English and
  Turkish grounded answers, trusted citations, citation-free insufficient evidence, and zero loaded
  models afterward.
- Phase 7 manual Streamlit smoke: Passed for application layout, 50 MB upload limit, local upload,
  synchronous indexing, Ready status, grounded answer, citation display, insufficient evidence,
  duplicate handling, rerun behavior, and no raw browser error.
- Phase 7 `uv run pytest -m "not foundry"`: Passed, 185 tests passed.
- Phase 7 coverage: Passed, 84% total coverage.
- Phase 7.1 targeted retrieval/RAG/UI checks: Passed.
- Phase 7.1 `uv run pytest -m "not foundry"`: Passed, 191 tests passed.
- Phase 7.1 coverage: Passed, 191 tests passed, 80% total coverage.
- Phase 7.1 fake-provider UI pipeline: Passed.
- Phase 7.1 real Foundry UI-backend smoke: Passed with local embeddings and chat.
- Phase 7.1 manual Streamlit browser smoke: Passed for chat-first layout, sidebar upload, language,
  performance mode, multiple-file input, bottom chat input, and greeting response.
- Phase 7.1 deterministic greeting timing smoke: Passed in 0.07 ms with zero model calls and zero
  citations.
- Phase 7.1.1 targeted logging/upload/UI checks: Passed, 31 tests passed.
- Phase 7.1.1 `uv run pytest -m "not foundry"`: Passed, 203 tests passed.
- Phase 7.1.1 coverage: Passed, 203 tests passed, 79% total coverage.
- Phase 7.1.1 fake-provider UI pipeline: Passed with automatic indexing, trusted citation,
  duplicate detection, persistence, and insufficient-evidence behavior.
- Phase 7.1.1 real Foundry UI-backend smoke: Passed with local embeddings, English and Turkish
  grounded answers, citations, and no loaded models afterward.
- Phase 7.1.1 manual Windows Streamlit smoke: Passed for automatic sequential DOCX/PDF processing,
  later-file success after a corrupt PDF, inline retry recovery, duplicate skipping, gear settings,
  rerun protection, grounded follow-up chat with citation, New chat document preservation, no raw
  traceback, no logging `OSError`, and zero loaded models afterward.
- Phase 7.2 targeted router/RAG/UI checks: Passed, 74 tests passed.
- Phase 7.2 `uv run pytest -m "not foundry"`: Passed, 228 tests passed.
- Phase 7.2 coverage: Passed, 228 tests passed, 79% total coverage.
- Phase 7.2 Foundry check: Passed; Foundry server `Ready`, 4 cached candidate models, local service
  reachable.
- Phase 7.2 fake-provider UI pipeline: Passed.
- Phase 7.2 real Foundry UI smoke: Passed with local embeddings, English/Turkish grounded answers,
  insufficient evidence, and trusted citations.
- Phase 7.2 Streamlit startup smoke: Passed on port 8512 with HTTP 200, then the test instance was
  stopped.
- Phase 7.2 manual real-document smoke: Passed for invalid input, greeting, Mercedes chassis,
  Mercedes engine, Turkish design, image-only PDF rejection, unrelated World Cup insufficient
  evidence, and small TXT fact answer.
- Pre-Phase 7 targeted indexing tests: Passed, 7 tests passed.
- Pre-Phase 7 fake-provider UI-backend pipeline timing smoke test: Passed.
- `uv sync`: Passed.
- `uv run ruff check .`: Passed.
- `uv run ruff format --check .`: Passed, 121 files already formatted.
- `uv run mypy src`: Passed, no issues in 76 source files.
- `uv run pytest -m "not foundry"`: Passed, 135 tests passed.
- `uv run python scripts/check_foundry.py`: Passed; Foundry CLI `0.10.2`, server `Ready`, 4 cached
  models, 0 loaded models at check time.
- Pre-Phase 7 real local end-to-end RAG smoke test: Passed with cached `qwen3-embedding-0.6b` and
  `phi-3.5-mini`, 1 indexed chunk, grounded answer, and 1 citation.
- Post-smoke `foundry status`: Passed; service `Ready`, local service `Reachable`, 4 cached models,
  and 0 loaded models.
- `uv run pytest --cov=groundnote --cov-report=term-missing`: Passed in Phase 6, 134 tests passed,
  83% total coverage.
- Streamlit startup smoke test: Passed.
- Phase 4 targeted chunking and ingestion tests: Passed, 16 tests passed.
- Phase 5 targeted embedding, indexing, and retrieval tests: Passed, 13 tests passed.
- Real Foundry embedding smoke test: Passed, 3 vectors, 1024 dimensions, finite float32 values.
- Real end-to-end indexing and retrieval smoke test: Passed.
- Phase 6 targeted RAG tests: Passed, 33 targeted unit and integration tests passed.
- Real Foundry chat smoke test: Passed with `phi-3.5-mini`, English and Turkish responses, valid
  `[S1]` citations, and `0` loaded models afterward.
- Real local end-to-end RAG smoke test: Passed with real local embeddings, real local chat,
  citation metadata, and insufficient-evidence behavior.

## Model Benchmark Status

- Existing Phase 1 benchmark remains valid.
- Phase 2 did not rerun full model benchmarks.
- Selected models remain:
  - Default chat model: `phi-3.5-mini`
  - Low-resource fallback chat model: `qwen2.5-0.5b`
  - Embedding model: `qwen3-embedding-0.6b`

## Known Issues

- `uv` is installed but is not on PATH for this shell, so commands are run through the installed
  executable.
- `python` and `py` are not on PATH; the project uses managed Python 3.11.15 through `uv`.
- `pytest` may emit a non-failing cache warning because `.pytest_cache` cannot be written in this
  Windows workspace.
- Foundry Local CLI `0.10.2` uses `foundry server status`; `foundry service status` is not
  recognized in this installed preview version.
- Phase 4 did not initialize or call Foundry Local models. The final Phase 4 regression check
  reported Foundry service `Ready` with `0` loaded models.
- Phase 5 needed a one-time `qwen3-embedding-0.6b` download because Foundry status reported `0`
  cached models and initial load failed with a missing model path.
- After Phase 5 smoke tests, Foundry status reported service `Ready`, local service `Reachable`,
  `1` cached model, and `0` loaded models.
- Phase 6 started with Foundry server `Not running`; `foundry server start` was used and the server
  became `Ready`.
- `phi-3.5-mini` was downloaded for the Phase 6 real chat smoke because it was not cached at the
  start of real chat testing. `qwen2.5-0.5b` was also downloaded and tested as a low-resource
  fallback, but the final successful smoke used the preferred `phi-3.5-mini` model.
- Phase 7.1 model operations remain synchronous. Balanced mode keeps models warm during the session,
  Fast uses the low-resource chat model, and Memory saver unloads after each operation.
- Phase 7.2 automatic processing remains synchronous and sequential; it is not a background queue.
  Document deletion and full Knowledge Base management remain Phase 8 work.
- Phase 7.2 materially improves the observed 81.726 s unrelated-question path to 0.546 s by
  returning insufficient evidence before chat generation.
- Phase 7.2 deterministic context answers are intentionally narrow and evidence-gated. General
  document questions still use the local chat model and may remain slower than deterministic paths.
- Manual Phase 7.2 indexing remained slow for medium PDFs on CPU: MB PDF 98.081 s and Turkish
  design PDF 107.257 s. Duplicate detection and warm embedding reuse are improved, but full
  background indexing and broader indexing controls remain future work.
- A parse failure that occurs before persistence can be retried while the browser still supplies the
  selected upload; after the file is unavailable, the user must select it again.
- Real Foundry Phase 7.1 smoke timings were measured on a tiny safe fixture:
  - indexing: 5.316 s
  - English grounded answer: 20.919 s
  - Turkish grounded answer: 12.946 s
  - insufficient-evidence answer: 12.969 s
  These are materially below the reported 73.93 s case but still synchronous local inference.

## Pre-Phase 6 Audit Notes

- The pre-Phase 6 audit found and fixed privacy-safe representation gaps so model `repr(...)`
  output no longer includes document text, query text, answer text, or raw vector values.
- The audit also found a Foundry Local preview SDK load-path issue for
  `qwen3-embedding-0.6b-generic-cpu:1`. The embedding provider now falls back to the local Foundry
  daemon on `127.0.0.1` for the same local embedding model variant when direct SDK loading fails.
- Real embedding smoke after the fix passed with 3 vectors, 1024 dimensions, finite float32 values,
  and `0` loaded models after unload.

## Environment Facts

- OS: Microsoft Windows 11 Pro, version 10.0.22621, 64-bit.
- Foundry Local CLI: `0.10.2`.
- Foundry Local SDK: `foundry-local-sdk-winml` `1.2.3`.
- Managed Python: 3.11.15.
- `uv`: 0.11.29.

## Next Phase

Phase 8: Knowledge Base Management, Delete, Re-index, and Index Controls.
