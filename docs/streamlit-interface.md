# Streamlit Interface

Phase 7.1.1 provides GroundNote's chat-first local user interface. It connects automatic secure
document processing, hybrid retrieval, and grounded RAG services without duplicating their
business logic.

## Start The Interface

Start Foundry Local when model operations are needed:

```powershell
foundry server start
```

Then launch GroundNote from the repository root:

```powershell
uv sync
uv run streamlit run src/groundnote/app.py
```

The application starts without loading an embedding or chat model. The sidebar performs only a
lightweight `foundry server status` check and never starts the service or downloads a model.

## Layout

The main header contains a compact gear popover for interface language, answer-language behavior,
performance mode, a disabled-by-default debug details toggle, and local model unloading. These
controls do not load a model or restart document processing.

The simplified sidebar contains:

- New chat;
- multiple-file upload;
- a compact Documents list with safe status labels, inline retry for failed documents, and a
  minimal confirmed remove action;
- optional collapsed source filters;
- Foundry Local status (`Ready`, `Not running`, `Unavailable`, or `Unknown`);
- a small local-only and OCR notice.

The main area is the conversation. It shows assistant/user messages, compact citations, and a
bottom chat input. Technical retrieval details are hidden from the normal answer flow.

## Documents View

The upload control accepts multiple `.pdf`, `.docx`, `.txt`, `.md`, or `.markdown` files. Streamlit and
the authoritative backend validation both use the default 50 MB upload limit. Browser MIME values
are not trusted.

Documents are automatically processed and indexed after selection. Processing is sequential and
locally executed; this is not a background queue. No separate processing or indexing button is
required:

1. write the bytes under the application-controlled document directory with a collision-resistant
   stored filename;
2. validate the file type, signature, filename, and size;
3. calculate SHA-256 and check for an exact duplicate;
4. parse and chunk the document through the existing ingestion service;
5. persist metadata and chunks as `PENDING_EMBEDDING`;
6. load the local embedding model and generate validated float32 embeddings;
7. persist embeddings and mark the document `INDEXED`;
8. keep the embedding model warm in Balanced/Fast mode or unload it in Memory saver mode.

The UI reports real stage boundaries rather than estimated percentages. A successful summary shows
only safe metadata: original filename, type, size, page/section counts when available, chunk counts,
status, embedding model, warnings, and duration. Stored UUID filenames, paths, hashes, document
text, and vectors are not shown.

Exact duplicates are not parsed, chunked, or indexed again. The temporary duplicate copy is removed
and the existing safe filename and status are displayed as an informational result. The user-facing
message explains that the file was already uploaded and was not processed again.

If a PDF appears to be image-only and no text can be extracted, it is not embedded and is not marked
ready. The UI explains that OCR is not available in the MVP and asks for a text-based PDF or another
supported format.

One failed file does not prevent later valid files from processing. Exact duplicates are reported
per file and are not re-indexed. A small **Retry** action appears beside the affected failed
document. Failed documents that reached local persistence reuse their existing document and chunk
identity; force retry clears incomplete embeddings before rebuilding them. A parse failure that did
not create a document requires the file to remain selected or be selected again. Uploaded bytes are
never copied into GroundNote session state.

The compact statuses are Waiting, Validating, Processing, Indexing, Ready, Already added, and
Failed. UUID stored filenames, hashes, raw errors, chunk identifiers, embedding details, and local
paths are not displayed.

The remove action deletes the selected document record and local index rows from SQLite after
confirmation. It does not delete the user's original source file from disk and does not affect other
indexed documents. Deleted documents are excluded from future retrieval and document inventory
answers.

## Ask GroundNote View

Only `INDEXED` documents appear as optional source filters in the sidebar. Users may select
documents and file types; empty selections mean all indexed documents. The selected IDs are
validated against current indexed records before a RAG request is created.

Each submitted document question:

1. validate the question and current source filters;
2. call the existing RAG service once;
3. embed the query and retrieve local chunks;
4. keep or unload the embedding model according to the selected performance mode;
5. generate with the local chat model when usable context exists;
6. keep or unload the chat model according to the selected performance mode;
7. validate citations and render the answer.

Empty input, unclear short input, greetings, thanks, and app-help messages return immediate
localized responses without retrieval, embedding, or chat model loading. Examples such as `A`, `?`,
`asd`, `asdf`, and `aaaa` are treated as unclear. Short automotive and technical terms such as
`W123`, `NVH`, `CRC`, `VIN`, `HTTP`, and `API` remain valid document queries.

Document inventory questions such as "What documents are indexed?", "List my uploaded documents",
and "Group the documents I uploaded" are answered from indexed document metadata. They do not call
retrieval or the chat model and do not fabricate page citations.

If no document is ready, GroundNote answers locally that the user should upload a document or wait
for processing. If at least one document is ready, questions can proceed against ready documents
while later uploads are still processing.

Conversation history is stored only in `st.session_state`. It is not persisted to SQLite.

## Answers And Citations

Grounded answers are rendered as Markdown with validated inline IDs such as `[S1]`. Model-generated
HTML is never enabled with `unsafe_allow_html=True`. Structured source cards are built from trusted
retrieval metadata, not model-generated filenames or page numbers.

Citation labels use:

- PDF: safe original filename and 1-based page number;
- DOCX and Markdown: safe original filename and section title;
- TXT: safe original filename and 1-based chunk number.

Unknown citation IDs never become trusted sources. If retrieval finds no usable evidence, or the
model explicitly reports that the supplied sources lack enough evidence, GroundNote returns a
deterministic insufficient-evidence message with no citations and no grounded-success label.
Turkish questions continue to produce Turkish answers and English questions produce English
answers.

The answer postprocessor detects repeated words, repeated phrases, repeated citation markers, and
runaway tails. It trims a useful cited prefix when possible, retries once with stricter instructions
when needed, and otherwise returns a localized safe repetition message.

Normal answers show the answer and compact sources. Internal router decisions, warning codes,
retrieval scores, and model/debug details are hidden unless the user enables **Show debug details**
in the settings popover.

## Session And Rerun Behavior

`st.session_state` contains safe message models, current filter IDs, and an upload lifecycle made of
opaque file identities, queued/completed/failed identity sets, compact statuses, and a structured
operation record. It does not contain uploaded bytes, embeddings, model instances, database
connections, transactions, or persistent chat history.

The application context is cached as a Streamlit resource because it contains stateless service
composition and lazily initialized provider objects. SQLite connections remain short-lived and are
never cached. Uploaded bytes, extracted text, prompts, answers, and vectors are not cached.

Stable upload identities combine safe filename, size, and a local content fingerprint. Completed
and failed identities are not automatically queued again on Streamlit reruns, language changes,
settings changes, chat submission, or New chat. SHA-256 database duplicate detection remains the
authoritative content-level fallback. Structured operations record an ID, type, file identity,
start/completion time, and terminal status. `try/finally` releases active state, and stale operations
are detected after a bounded interval.

## Windows Logging And Safe Errors

GroundNote uses Structlog through Python standard-library logging. A UTF-8 rotating file handler
opens and closes the local file for each record; no cached Structlog `PrintLogger` retains
Streamlit's temporary `sys.stdout` or `sys.stderr` stream across reruns. Reconfiguration is
idempotent. A narrow
best-effort logging helper ensures a closed stream, invalid Windows handle, `OSError(22)`, or handler
failure cannot replace the original application error or prevent operation-state cleanup.

Streamlit `client.showErrorDetails` is set to `"none"`. Normal UI error paths map the original
exception to localized safe text. Browser users do not receive absolute paths, usernames,
tracebacks, source frames, exception bodies, SQL, prompts, or dependency internals. Local logs keep
only privacy-safe event names, categories, counts, statuses, and durations.

## Privacy And Model Lifecycle

- Uploads, SQLite data, embeddings, questions, and answers remain on the local machine.
- No Azure OpenAI, paid cloud API, or cloud fallback exists.
- Model downloads require internet once; cached inference is local.
- Selecting a file, starting the app, and refreshing status load no model.
- Balanced and Fast modes may keep models warm after first use.
- Balanced unloads idle models after a short local idle TTL.
- Fast keeps models warm longer and may use more RAM.
- Memory saver unloads models after each operation and uses a shorter idle TTL.
- Sequential uploads reuse a warm embedding provider inside the session when the selected mode
  allows it.
- The UI avoids starting indexing and answer generation at the same time in the normal Streamlit
  flow.
- Chat models are unloaded before document indexing when safe.
- Model inference does not run while a SQLite write transaction is held.
- Logs contain safe counts, categories, model names, statuses, and durations—not private content.

## Troubleshooting

If the sidebar reports **Not running** or a model operation fails, run:

```powershell
foundry server status
foundry server start
```

If a model is unavailable, confirm that the configured alias is present and cached using the
project's Foundry setup documentation. GroundNote never downloads a model merely to render status.

Scanned or image-only PDFs require OCR, which is outside the MVP. Export a text-based PDF or use a
supported text format. Encrypted PDFs must be decrypted locally before upload.

## Known Limitations

- No OCR.
- Minimal single-document removal exists, but full Knowledge Base management is not implemented.
- No force re-index or bulk indexing UI.
- No full Knowledge Base management screen.
- No background jobs or task queue; automatic indexing and answers are synchronous.
- No persistent or history-aware conversation.
- Local semantic retrieval and local language models can make mistakes.

## Phase 7 Verification Measurements

The real local smoke used one original temporary Markdown document, cached
`qwen3-embedding-0.6b`, and cached `phi-3.5-mini`:

| Operation | Measured time |
| --- | ---: |
| Index one chunk | 5.515 s |
| English grounded RAG request | 14.971 s |
| Turkish grounded RAG request | 15.603 s |
| No-evidence retrieval request | 1.782 s |

The smoke produced one 1024-dimensional indexed chunk, one trusted citation for each grounded
answer, a citation-free insufficient-evidence result, and zero loaded Foundry models afterward.
Measurements are specific to the current development machine and short smoke fixture.

Phase 7 is complete only when its tests, real local smoke, manual Streamlit smoke, documentation,
and quality checks pass. Phase 8 has not started.

## Phase 7.2 Manual Measurements

Phase 7.2 real-document smoke used cached Foundry Local models and the user's local MB
nomenclature and Turkish design PDFs. Representative measured results:

| Operation | Measured time |
| --- | ---: |
| Invalid inputs `A`, `?`, `asdf` | 0.000 s |
| Greeting `Merhaba` | 0.000 s |
| Mercedes chassis answer, cold retrieval | 5.658 s |
| Mercedes chassis answer, warm retrieval | 0.437 s |
| Mercedes engine answer, warm retrieval | 0.466 s |
| Turkish design answer, warm retrieval | 0.430 s |
| Unrelated World Cup question | 0.546 s |
| Small TXT fact answer | 0.578 s |

The unrelated World Cup question no longer reaches chat generation when the retrieved context lacks
plausible overlap with the question. Medium PDF indexing is still synchronous and CPU-bound; the
same smoke measured 98.081 s for the MB PDF and 107.257 s for the Turkish design PDF.
