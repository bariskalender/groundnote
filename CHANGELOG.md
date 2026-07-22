# Changelog

GroundNote follows Semantic Versioning for public pre-releases. Until `1.0.0`, minor releases may
contain intentional compatibility changes documented here; patch releases should remain backward
compatible bug fixes.

## [0.9.0] - 2026-07-22

### Added

- Windows setup, environment doctor, launcher, scoped stop, and release archive workflows.
- Programmatic application version metadata.
- Deterministic portable ZIP packaging that excludes private/local data and model files.
- Packaging strategy and release checklist documentation.
- Privacy-safe indexing stage diagnostics, real chunk progress, and an isolated indexing benchmark.

### Security and privacy

- Launcher binds Streamlit to loopback only and records a random session token for scoped cleanup.
- Doctor output excludes private paths, environment values, documents, prompts, vectors, and keys.
- No telemetry, cloud API, model bundle, or automatic model download was added.
- Topic-specific factual shortcuts were removed so unrelated evidence cannot receive a false
  grounded citation.
- Remove and clear-all delete only canonically validated GroundNote-managed copies; external
  originals, traversal targets, symlinks/reparse points, and unrelated files are never removed.

### Fixed

- Ready now requires complete chunks, compatible float32 embeddings, matching model metadata, and
  consistent FTS rows.
- Bootstrap reconciles interrupted indexing and incomplete indexes into a retryable,
  non-searchable state without affecting unrelated Ready documents.
- Indexing failures clean partial embeddings and FTS rows, and final Ready status is gated by an
  integrity check in the committing transaction.
- Managed upload copies no longer remain silently after successful Remove or Clear all actions;
  partial filesystem cleanup is reported with a sanitized localized warning.
- Fast and Balanced mode switches now keep at most one GroundNote-owned chat provider active, and
  provider/client/generation failures release only GroundNote-owned resources.
- Indexing and query failure paths now release embedding resources, while RAG releases embeddings
  before loading chat.
- Upload indexing reuses the already-read bytes and SHA-256 digest instead of rereading and hashing
  the same content.

### Existing product baseline

- Offline-first PDF, DOCX, TXT, and Markdown ingestion.
- Local SQLite metadata, chunks, and float32 embeddings.
- Local hybrid retrieval and Foundry Local grounded answers with citations.
- Knowledge Base removal, clear-all, re-index, session-only chat, and English/Turkish UI.
