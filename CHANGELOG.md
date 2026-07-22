# Changelog

GroundNote follows Semantic Versioning. The 1.0.0 release is the completed portfolio baseline;
future compatibility changes will be documented here.

## [1.0.0] - 2026-07-22

### Added

- Final public README with verified capabilities, setup, architecture, privacy, safety limits,
  performance evidence, testing, release, and limitation guidance.
- Implemented architecture documentation with component, indexing, RAG, model lifecycle, and
  browser-refresh ownership diagrams.
- Original redistribution-safe Lantern Lab handbook, demonstration questions, demo script, and
  English/Turkish presentation outlines.
- Contribution and security policies plus practical GitHub issue and pull request templates.
- Privacy-safe application screenshots created only from the original demonstration material.

### Changed

- Promoted the canonical package and portable archive version from 0.9.0 to 1.0.0.
- Consolidated the public roadmap and project state around completed product phases and future
  enhancements rather than temporary stabilization labels.
- Extended the portable source archive allowlist with public contribution/security guidance and
  demonstration examples while retaining all private/generated exclusions.
- Standardized documented environment-variable names on their canonical settings fields.
- Removed unused legacy Streamlit page/component adapters and stale superseded settings; moved the
  DOCX fixture writer to development-only dependencies because runtime parsing uses bounded standard
  library ZIP/XML processing.

### Verified release baseline

- One-file-at-a-time synchronous indexing with process-local refresh ownership and authoritative
  Ready integrity checks.
- Bounded PDF/DOCX processing, local-only Foundry inference, privacy-safe diagnostics, and scoped
  Windows launcher cleanup.
- Deterministic portable archive and filename-only SHA-256 sidecar; generated release artifacts
  remain untracked.

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
- PDF/DOCX expansion, extracted text, and generated chunks are bounded before embedding; DOCX ZIP
  traversal, encryption, special entries, and compression abuse are rejected without extraction.
- Release archives reject symlink/reparse boundary crossings, exclude current/prior release
  artifacts, and include a deterministic SHA-256 sidecar without an absolute path.
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
- Restored one-file-at-a-time upload after manual product testing showed that multi-file selection
  added state complexity without reducing CPU-bound embedding time.
- Browser refreshes now preserve genuinely active indexing ownership, block duplicate work and
  retrieval, and show Ready only after the complete index transaction commits and ownership ends.
- Windows release setup installs runtime dependencies only and treats an installed but stopped
  Foundry service as a warning that the launcher resolves.
- Launcher startup/metadata failures now terminate only token-owned child processes and remove
  partial session metadata.
- Foundry diagnostics distinguish stopped, starting, ready, unavailable, and unknown states while
  keeping executable/profile paths out of shareable output and localizing Streamlit status text.

### Existing product baseline

- Offline-first PDF, DOCX, TXT, and Markdown ingestion.
- Local SQLite metadata, chunks, and float32 embeddings.
- Local hybrid retrieval and Foundry Local grounded answers with citations.
- Knowledge Base removal, clear-all, re-index, session-only chat, and English/Turkish UI.
