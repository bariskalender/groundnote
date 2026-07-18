# Project State

## Current Phase

Phase 2: Configuration, Domain Models, and SQLite Storage.

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

## Commands Run In Phase 2

- `uv sync`
- `uv run ruff check .`
- `uv run ruff check . --fix`
- `uv run ruff format --check .`
- `uv run mypy src`
- `uv run pytest -m "not foundry"`
- `uv run pytest --cov=groundnote --cov-report=term-missing`
- `uv run streamlit run src/groundnote/app.py`

## Test Status

- `uv sync`: Passed.
- `uv run ruff check .`: Passed.
- `uv run ruff format --check .`: Passed.
- `uv run mypy src`: Passed.
- `uv run pytest -m "not foundry"`: Passed, 46 tests passed.
- `uv run pytest --cov=groundnote --cov-report=term-missing`: Passed, 46 tests passed, 72%
  total coverage.
- Streamlit startup smoke test: Passed.

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

## Environment Facts

- OS: Microsoft Windows 11 Pro, version 10.0.22621, 64-bit.
- Foundry Local CLI: `0.10.2`.
- Foundry Local SDK: `foundry-local-sdk-winml` `1.2.3`.
- Managed Python: 3.11.15.
- `uv`: 0.11.29.

## Next Phase

Phase 3: Secure Document Validation and Parsing.
