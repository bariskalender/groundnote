# Pre-Phase 7 UI Readiness Audit

Date: 2026-07-20

## Scope

This audit reviewed Phases 0-6 before connecting the backend pipeline to the Phase 7 Streamlit
upload, indexing, and chat interface. Phase 7 UI work was not started.

Reviewed flow:

```text
startup -> configuration -> database bootstrap -> uploaded-file writing -> validation
-> duplicate detection -> parsing -> chunking -> persistence -> embedding indexing
-> semantic retrieval -> grounded RAG generation -> citations -> UI-safe responses
```

## Initial Repository State

- Branch: `main`.
- Remote: `https://github.com/bariskalender/groundnote.git`.
- `main` was synchronized with `origin/main` before audit work began.
- Working tree was clean before audit work began.
- Phase 6 commit `4a6f06e feat: add grounded RAG generation and citations` was present.
- Phase 7 had not started.
- No private documents, model files, SQLite databases, logs, caches, or generated local data were
  found tracked. Security filename matching reported expected false positives for source/test
  paths containing `documents` and the intentional `data/documents/.gitkeep` placeholder.

## Findings

### Fixed: indexing held a database transaction during local embedding inference

The Phase 5 indexing service opened one SQLite Unit of Work before loading the embedding model,
batching chunk content, generating embeddings, serializing vectors, and saving the final indexed
state. This preserved atomic visibility, but it also held a write transaction during slow local
model work. Under Streamlit reruns, this could make status polling, retries, or nearby document
operations wait unnecessarily.

Fix:

- Indexing now uses a short transaction to validate status and move the document to `INDEXING`.
- Local embedding model loading and generation run outside the write transaction.
- Final embedding BLOB persistence and `INDEXED` status update happen in one short transaction.
- If embedding generation fails, the document is marked `FAILED` with a safe error message and
  remains non-searchable.
- Retrieval still loads only `INDEXED` documents with compatible embedding model/version metadata.

Regression coverage:

- Added a test proving a separate SQLite write can complete while the fake embedding provider is
  generating vectors.
- Updated failure behavior tests to assert `FAILED` remains non-searchable and contains only a safe
  error message.

## Audit Results

### Application composition

- Startup remains lightweight and explicit.
- Importing modules does not load chat or embedding models.
- `initialize_application()` performs settings loading, directory initialization, and idempotent
  migrations only.
- Dependencies are constructed explicitly and are suitable for later Streamlit caching.
- SQLite connections are created per Unit of Work or short read operation; no global cursor or
  shared transaction was found.

### Streamlit rerun readiness

- Backend services do not rely on terminal input or a long-lived web request context.
- Model providers are explicit dependencies and can be cached carefully in Phase 7 without changing
  domain code.
- Duplicate SHA-256 checks remain authoritative.
- Retrying ingestion of the same exact file stops before expensive parsing/chunking.
- Retrying indexing of an indexed document is rejected unless force re-index is explicitly selected.
- Failed indexing is visible through document status and can be handled as a recoverable UI state.

Phase 7 recommendation: cache settings, database path/factories, and provider managers explicitly;
do not cache SQLite connections across Streamlit reruns.

### UI service boundary

The future UI can call high-level services for:

- uploaded-byte writing through `write_uploaded_bytes()`;
- document ingestion through `PreEmbeddingIngestionService`;
- indexing, status checks, clearing, and force re-indexing through `DocumentIndexingService`;
- semantic retrieval through `SemanticRetrievalService`;
- grounded answers and citations through `RagService`.

The UI should not need to execute SQL, instantiate parser libraries, construct prompts, call
Foundry providers directly, decode embedding BLOBs, or parse SDK responses.

Phase 7 recommendation: add a thin UI adapter for mapping backend exceptions into display-ready
messages instead of embedding that mapping directly in Streamlit widgets.

### User-safe error contract

- Document validation distinguishes unsupported file type, too-large file, empty file, unsafe path,
  encrypted PDF, corrupt document, no extractable text, encoding issues, duplicates, and missing
  parser.
- Embedding/indexing errors distinguish model load, generation, malformed vectors, partial
  embeddings, already-indexed documents, and not-ready documents.
- Retrieval rejects empty queries and safely wraps malformed stored embeddings.
- RAG rejects empty/oversized questions, retrieval errors, prompt construction errors, chat
  provider failures, invalid chat responses, and citation validation failures.
- Logging and model representations avoid raw document content, prompts, full queries, generated
  answers, raw vectors, and absolute paths.

Phase 7 recommendation: expose these as short UI categories such as unsupported file, duplicate,
indexing failed, model unavailable, no relevant evidence, and generation failed.

### Upload lifecycle

- Uploaded bytes are written under an application-controlled target directory.
- Display filenames are normalized separately from UUID-prefixed stored filenames.
- Traversal components are rejected and absolute/path-like names are reduced to safe filename
  components.
- Writes use binary exclusive create mode, avoiding accidental overwrite.
- Parser failure does not persist database records because ingestion writes happen after parsing and
  chunking succeed.
- User uploads are not inside the Git repository by default.

Phase 7 recommendation: delete temporary duplicate upload copies after duplicate detection if the
UI writes bytes before ingestion.

### Document pipeline regression

- PDF, DOCX, TXT, and Markdown support remains covered by tests.
- PDF page numbers remain 1-based.
- DOCX/Markdown section metadata survives into chunks and citations.
- Stored UUID filenames are separate from user-facing original filenames.
- Pre-embedding ingestion does not load Foundry Local models.
- Parser/chunking/storage failures roll back partial document records.

### Indexing and model lifecycle

- Application startup loads no model.
- Embedding indexing loads only the embedding provider and unloads it afterward.
- Retrieval loads the embedding provider for the query and unloads it afterward.
- Chat generation is isolated in the RAG service and unloads the chat provider afterward.
- Local Foundry daemon fallbacks remain restricted to loopback addresses.
- Failed or partial embeddings are not searchable because retrieval requires `INDEXED` document
  status and compatible model/version metadata.

### RAG and citations

- `RagAnswer` exposes answer text, citations, grounded flag, insufficient-evidence flag, resolved
  language, model, prompt version, counts, warnings, and duration.
- Citation metadata is built from trusted retrieval metadata, not generated model text.
- Citation IDs are validated against selected context IDs.
- Unknown citation IDs cannot become trusted citations.
- Insufficient-evidence responses return no fake citations.
- Stored UUID filenames and absolute paths are not displayed.

### Privacy and logging

- Privacy regression tests cover model representations for query text, answer text, chunk content,
  prompts, and vectors.
- Logs include safe counts, statuses, model names, dimensions, durations, and warning categories.
- Logs do not include uploaded bytes, extracted document content, chunk content, full queries,
  prompts, generated answers, raw vectors, embedding BLOBs, credentials, or absolute paths.

### SQLite concurrency

- Unit of Work scopes are explicit and close connections on exit.
- Foreign keys and busy timeout are enabled per connection.
- Migrations are idempotent.
- After the audit fix, local model inference is outside write transactions.
- A future progress UI can poll document status without competing with a long-running embedding
  transaction.

### Settings and dependencies

- `.env.example`, typed settings, and documentation agree on model aliases, chunking defaults,
  retrieval defaults, RAG defaults, upload size, embedding dimension, dtype, and version.
- No cloud endpoint or secret is required.
- Dependencies remain local-MVP appropriate: Streamlit, SQLite, NumPy, Pydantic, Foundry Local SDK,
  document parsers, and development tooling.
- No LangChain, LlamaIndex, vector database, OCR package, cloud inference SDK for runtime model
  selection, or unsafe serialization dependency was added.

## Representative Smoke Measurements

Measured with deterministic fake providers and temporary local storage:

| Operation | Time |
| --- | ---: |
| Settings directory bootstrap | 1.113 ms |
| SQLite migrations | 11.491 ms |
| Uploaded Markdown write | 0.582 ms |
| Markdown ingestion and chunking | 12.234 ms |
| Fake-provider indexing | 6.660 ms |
| Semantic retrieval | 2.335 ms |
| Fake-provider RAG answer | 0.928 ms |

Pipeline result:

- chunks: `1`
- indexed chunks: `1`
- citations: `1`
- grounded answer: `true`

## Real Local Foundry Smoke

Also verified one temporary Markdown document with cached local Foundry models:

- embedding model: `qwen3-embedding-0.6b`
- chat model: `phi-3.5-mini`
- indexed chunks: `1`
- grounded answer: `true`
- citation count: `1`
- warnings: `[]`
- post-smoke Foundry status: service `Ready`, local service `Reachable`, cached models `4`, loaded
  models `0`

Observed durations from application logs:

| Operation | Time |
| --- | ---: |
| Markdown ingestion and chunking | 19.617 ms |
| Real local embedding indexing | 5576.305 ms |
| Real local semantic retrieval | 2500.804 ms |
| Real local grounded RAG answer | 24882.027 ms |

## Security Search Summary

Reviewed for hard-coded API keys, passwords, tokens, cloud endpoints, arbitrary remote URLs,
user-controlled subprocess commands, unsafe pickle use, SQL interpolation, shell execution, prompt
logging, answer logging, raw vectors, absolute personal paths, private documents, SQLite files, log
files, model files, caches, and upload directories.

No blocking security issue was found. The only remote-looking runtime usage is the intentional
OpenAI-compatible client pointed at a Foundry Local loopback URL with a dummy local API key.

## Known Limitations Before Phase 7

- There is still no final Streamlit upload, indexing, Knowledge Base, or chat UI.
- There is no persistent chat memory.
- There is no background job queue or progress callback framework.
- Document deletion is available at repository level but no UI workflow exists yet.
- A small UI error-mapping adapter should be added in Phase 7 for consistent user-facing messages.
- First-time model downloads require internet; cached inference is intended to work locally.

## Conclusion

GroundNote Phases 0-6 now form a UI-ready backend foundation for Phase 7. The one concrete
readiness defect found during the audit was fixed. The backend remains local-only, avoids cloud
inference, preserves privacy boundaries, and exposes enough service-level operations for the
Streamlit interface to be implemented next.
