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
