# GroundNote Decisions

## ADR-0001: Use Python 3.11

- Status: Accepted
- Date: 2026-07-18

GroundNote will target Python 3.11. This matches the project requirement and gives a stable,
well-supported runtime for Streamlit, SQLite, NumPy, and local model integration work.

## ADR-0002: Use Streamlit For The UI

- Status: Accepted
- Date: 2026-07-18

GroundNote will use Streamlit for the user interface. Streamlit is suitable for a local desktop
study assistant because it keeps the UI simple, fast to iterate on, and Python-native.

## ADR-0003: Use SQLite For Local Persistence

- Status: Accepted
- Date: 2026-07-18

GroundNote will use SQLite for metadata, chunks, and embeddings. SQLite keeps the application
local-first, simple to install, and appropriate for a single-user study tool.

## ADR-0004: Use NumPy Cosine Similarity For Retrieval

- Status: Accepted
- Date: 2026-07-18

GroundNote will start with NumPy cosine similarity instead of a separate vector database. This
keeps the MVP understandable and avoids adding infrastructure before it is needed.

## ADR-0005: Use uv For Dependency Management

- Status: Accepted
- Date: 2026-07-18

GroundNote will use `uv` with `pyproject.toml`. This supports fast, reproducible local setup.
`uv.lock` will be generated when `uv` is available.

## ADR-0006: Do Not Use Cloud Providers

- Status: Accepted
- Date: 2026-07-18

GroundNote must not silently use Azure OpenAI, OpenAI APIs, or another cloud provider. Chat,
embeddings, documents, prompts, and logs must remain local unless the user explicitly approves a
different direction in a future conversation.

## ADR-0007: Use Project-Local uv Runtime Directories During Setup

- Status: Accepted
- Date: 2026-07-18

The formatted Windows environment had conflicts in the default `uv` cache path and access issues
in the default managed Python path. Phase 0 uses project-local `.uv-cache` and `.uv-python`
directories so setup and verification can proceed without changing broader user-profile state.

## ADR-0008: Use Foundry Local SDK WinML On Windows

- Status: Accepted
- Date: 2026-07-18

GroundNote uses `foundry-local-sdk-winml` on Windows and `foundry-local-sdk` only on macOS through
mutually exclusive environment markers. The installed Windows SDK version is `1.2.3`. The SDK is
isolated behind provider interfaces so preview API changes remain contained.

## ADR-0009: Use SDK-Selected CPU Variants For Initial Benchmarks

- Status: Accepted
- Date: 2026-07-18

The CLI catalog lists GPU as the default hardware target for the Phase 1 aliases, but the
project-local SDK benchmark resolved and ran CPU variants for `phi-3.5-mini`, `qwen2.5-0.5b`, and
`qwen3-embedding-0.6b`. This is conservative and reliable on the development machine. GPU
availability was detected, but no GPU-specific alias or variant was forced in Phase 1.

## ADR-0010: Keep Initial Model Defaults

- Status: Accepted
- Date: 2026-07-18

Benchmarks showed both chat candidates can answer a trivial prompt, and the embedding candidate
returns finite 1024-dimensional float32 vectors. GroundNote keeps `phi-3.5-mini` as the default
chat model, `qwen2.5-0.5b` as the low-resource fallback, and `qwen3-embedding-0.6b` for
embeddings.

## ADR-0011: Use Pydantic Settings With Explicit Bootstrap

- Status: Accepted
- Date: 2026-07-18

GroundNote uses `pydantic-settings` for typed configuration and `platformdirs` for default local
data paths. Importing settings does not create directories; directory and database initialization
run only through explicit bootstrap.

## ADR-0012: Use Lightweight SQLite Migrations And Unit Of Work

- Status: Accepted
- Date: 2026-07-18

GroundNote uses a small versioned SQL migration runner instead of Alembic. SQLite repositories do
not commit on every method; transaction boundaries are controlled by `SQLiteUnitOfWork` so future
document replacement and re-indexing workflows can be atomic.

## ADR-0013: Store Embeddings As float32 BLOB Values

- Status: Accepted
- Date: 2026-07-18

GroundNote serializes one-dimensional finite NumPy embeddings as contiguous `float32` bytes with
dimension and dtype metadata. Pickle and JSON embedding storage are intentionally avoided.
