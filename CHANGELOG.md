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

### Security and privacy

- Launcher binds Streamlit to loopback only and records a random session token for scoped cleanup.
- Doctor output excludes private paths, environment values, documents, prompts, vectors, and keys.
- No telemetry, cloud API, model bundle, or automatic model download was added.

### Existing product baseline

- Offline-first PDF, DOCX, TXT, and Markdown ingestion.
- Local SQLite metadata, chunks, and float32 embeddings.
- Local hybrid retrieval and Foundry Local grounded answers with citations.
- Knowledge Base removal, clear-all, re-index, session-only chat, and English/Turkish UI.
