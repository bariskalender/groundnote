# Project State

## Current Phase

Phase 4: Hybrid Recursive Chunking and Pre-Embedding Ingestion.

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

## Test Status

- `uv sync`: Passed.
- `uv run ruff check .`: Passed.
- `uv run ruff format --check .`: Passed.
- `uv run mypy src`: Passed.
- `uv run pytest -m "not foundry"`: Passed, 90 tests passed.
- `uv run pytest --cov=groundnote --cov-report=term-missing`: Passed, 90 tests passed, 83%
  total coverage.
- Streamlit startup smoke test: Passed.
- Phase 4 targeted chunking and ingestion tests: Passed, 16 tests passed.

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

## Environment Facts

- OS: Microsoft Windows 11 Pro, version 10.0.22621, 64-bit.
- Foundry Local CLI: `0.10.2`.
- Foundry Local SDK: `foundry-local-sdk-winml` `1.2.3`.
- Managed Python: 3.11.15.
- `uv`: 0.11.29.

## Next Phase

Phase 5: Embedding, Indexing, and Semantic Retrieval.
