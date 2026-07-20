# Project State

## Current Phase

Phase 6: RAG Generation, Prompt Safety, Citations, and Language Handling.

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

## Test Status

- `uv sync`: Passed.
- `uv run ruff check .`: Passed.
- `uv run ruff format --check .`: Passed.
- `uv run mypy src`: Passed.
- `uv run pytest -m "not foundry"`: Passed, 134 tests passed.
- `uv run pytest --cov=groundnote --cov-report=term-missing`: Passed, 134 tests passed, 83%
  total coverage.
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

Phase 7: Streamlit Upload, Indexing, and Chat Interface.
