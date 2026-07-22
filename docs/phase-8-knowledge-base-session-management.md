# Phase 8: Knowledge Base and Session Management

Phase 8 adds practical local document-management controls without changing GroundNote into a
cloud knowledge platform.

## What Was Added

- A localized **Knowledge Base** section in the Streamlit sidebar.
- Per-document filename, status, file type, chunk count, page count when available, and indexed
  timestamp when available.
- Confirmed **Remove** for one document.
- Confirmed **Clear all documents** for the entire GroundNote index.
- Sequential **Re-index** for one document using its existing locally persisted chunks.
- Empty-chat guidance that reflects whether indexed documents are available.
- New chat safety: it clears in-memory messages only and is unavailable while an operation is active.

## Data Safety

Remove and clear-all first remove document records, chunks, float32 embedding values, and FTS rows
in one SQLite transaction. They then delete only the corresponding GroundNote-managed copies after
canonical containment and reparse-point checks. They do not delete the original selected source
file, repository files, traversal targets, symlinks, or unrelated files in the managed directory.
If filesystem cleanup fails after the database commit, the index remains consistent and the UI
shows a sanitized partial-cleanup warning instead of claiming complete success.

Re-index clears and regenerates embeddings for the existing chunks. It does not parse a new copy of
the original file, add chunks, or duplicate FTS rows. If embedding generation fails, the document is
left in a safe failed/non-searchable state; preserving the prior vector version is intentionally not
claimed.

A document is shown as Ready only after its committed chunk count, compatible embeddings, document
model metadata, and FTS rows pass the centralized integrity check. Bootstrap treats transient
indexing state from a previous process as interrupted, clears partial embedding/search data, keeps
the committed chunks and managed copy needed for retry, and marks the document retryable. Incomplete
documents are excluded from inventory-ready counts, retrieval, and citations.

## Scope Intentionally Deferred

- OCR and image parsing.
- Re-index all documents: a synchronous bulk operation would be costly without a background queue.
- Background indexing workers or daemon processes.
- Persistent chat storage, cloud sync, accounts, or semantic conversation memory.
- Packaging, installers, and portfolio/visual polish.

## Privacy

All document actions remain local. No cloud API, telemetry, or external document transfer is added.
Technical errors remain hidden by default, and logs continue to redact document content, queries,
prompts, answers, vectors, paths, and secrets.

## Validation Focus

The Phase 8/9.1A suite verifies clear-all cleanup, managed-copy removal, external-original safety,
re-index chunk/file stability, interrupted recovery, Ready integrity, retrieval exclusion after
removal or incomplete indexing, New chat operation safety, localization, and privacy-safe logging.

## Phase 8.1 Stabilization

Manual validation found three Streamlit-specific issues and Phase 8.1 corrected them:

- Document actions are vertically stacked, full-width controls inside each card so English and
  Turkish labels remain readable when the sidebar is narrow.
- Upload registration checks the active operation before adding a new selection to session state.
  A blocked selection receives a localized busy message and the upload widget resets predictably;
  previously queued Waiting items can recover on the next idle rerun.
- Re-index success and safe failure feedback are stored as one-time, privacy-safe session notices.
  The notice survives the required rerun and is consumed after one render.

The application context cache is also separated by a hash of the local path configuration. This
prevents a rerun or test session that changes the local data directory from reusing composition for
another database, without storing or logging the raw path as the cache key.
