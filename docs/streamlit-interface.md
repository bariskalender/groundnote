# Streamlit Interface

Phase 7 provides GroundNote's first complete local user interface. It connects the existing secure
document, indexing, retrieval, and grounded RAG services without duplicating their business logic.

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

The sidebar contains:

- local privacy guidance;
- Foundry Local status (`Ready`, `Not running`, `Unavailable`, or `Unknown`);
- navigation between **Documents** and **Ask GroundNote**;
- supported-format and OCR notices;
- the configured embedding and chat model aliases.

The main heading describes GroundNote as a private, offline RAG study assistant. The persistent
footer notice reminds users that local models can make mistakes and important information should be
checked against cited sources.

## Documents View

The upload control accepts one `.pdf`, `.docx`, `.txt`, `.md`, or `.markdown` file. Streamlit and
the authoritative backend validation both use the default 50 MB upload limit. Browser MIME values
are not trusted.

Processing begins only after **Process and Index Document** is selected:

1. write the bytes under the application-controlled document directory with a collision-resistant
   stored filename;
2. validate the file type, signature, filename, and size;
3. calculate SHA-256 and check for an exact duplicate;
4. parse and chunk the document through the existing ingestion service;
5. persist metadata and chunks as `PENDING_EMBEDDING`;
6. load the local embedding model and generate validated float32 embeddings;
7. persist embeddings and mark the document `INDEXED`;
8. unload the embedding model.

The UI reports real stage boundaries rather than estimated percentages. A successful summary shows
only safe metadata: original filename, type, size, page/section counts when available, chunk counts,
status, embedding model, warnings, and duration. Stored UUID filenames, paths, hashes, document
text, and vectors are not shown.

Exact duplicates are not parsed, chunked, or indexed again. The temporary duplicate copy is removed
and the existing safe filename and status are displayed as an informational result.

The document status table displays original filename, type, status, file size, pages, chunk counts,
upload/index times, and embedding model. **Refresh document status** performs a short read only; it
does not parse, index, or load a model. Phase 7 intentionally has no delete, re-index, or complete
Knowledge Base management controls.

## Ask GroundNote View

Only `INDEXED` documents appear as optional source filters. Users may select documents and file
types; empty selections mean all indexed documents. The selected IDs are validated against current
indexed records before a RAG request is created.

Each submitted question is independent:

1. validate the question and current source filters;
2. call the existing RAG service once;
3. embed the query and retrieve local chunks;
4. unload the embedding model;
5. generate with the local chat model when usable context exists;
6. unload the chat model;
7. validate citations and render the answer.

The latest question and answer may remain in the current browser session. GroundNote does not store
persistent conversation history, reuse previous answers, or perform history-aware retrieval.

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

## Session And Rerun Behavior

`st.session_state` contains controlled flags, safe result models, the latest question/answer, and
current filter IDs. It does not contain uploaded bytes, embeddings, model instances, database
connections, transactions, or persistent chat history.

The application context is cached as a Streamlit resource because it contains stateless service
composition and lazily initialized provider objects. SQLite connections remain short-lived and are
never cached. Uploaded bytes, extracted text, prompts, answers, and vectors are not cached.

Button and chat-input event semantics prevent a normal rerun from repeating an operation. SHA-256
duplicate detection remains the authoritative fallback if a user explicitly submits identical
content again.

## Privacy And Model Lifecycle

- Uploads, SQLite data, embeddings, questions, and answers remain on the local machine.
- No Azure OpenAI, paid cloud API, or cloud fallback exists.
- Model downloads require internet once; cached inference is local.
- Selecting a file, starting the app, and refreshing status load no model.
- Embedding and chat models are loaded only for their operation and unloaded afterward.
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
- No document deletion UI.
- No force re-index or bulk indexing UI.
- No full Knowledge Base management screen.
- No background jobs or task queue; indexing and answers are synchronous.
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
