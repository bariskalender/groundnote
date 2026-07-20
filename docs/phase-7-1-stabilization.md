# Phase 7.1 Stabilization

Phase 7.1 is a corrective product-stabilization phase after manual Phase 7 testing.

## Confirmed Root Causes

- Retrieval loaded a pre-limited SQL slice before scoring vectors, so long documents and later
  documents could be starved.
- The UI sent every chat input through RAG, including greetings and help messages.
- The model lifecycle unloaded local models after each operation, making interactive chat slow.
- The main UI emphasized technical filters and status panels instead of the conversation.
- Session operation state used fragile booleans that could survive interrupted reruns.
- Insufficient-evidence handling still depended too much on exact refusal wording.

## Retrieval Changes

- All compatible `INDEXED` vectors are now eligible before global scoring.
- `retrieval_candidate_limit` is applied after ranking, not before cosine similarity.
- SQLite FTS5 backs lexical search over chunk content, section titles, and filenames.
- Hybrid ranking combines vector similarity, lexical matches, exact headings, numbered terms, and
  deterministic tie-breaking.
- Conservative typo expansion is retrieval-only. It supports one safe edit for unambiguous corpus
  terms such as `pehase` to `phase` without rewriting the user-visible question.
- Adjacent chunks from the same document and section may be included when they fit the context
  limits.

## RAG And UX Changes

- Greetings, thanks, and app-help messages return deterministic localized responses without
  retrieval, embedding, or chat model loading.
- Generation now asks for a `STATUS: supported` or `STATUS: insufficient` contract and parses it
  conservatively.
- Insufficient answers return `grounded=False`, `insufficient_evidence=True`, and no citations.
- Citation repair remains limited to one retry and runs only when a supported answer lacks valid
  citations.
- Balanced mode keeps models warm during the current app session. Fast mode uses the low-resource
  chat model with a lower output limit. Memory saver unloads models after each operation.

## Chat-First Interface

- The main view is now a conversation with a bottom chat input.
- The sidebar contains New chat, language, performance mode, Foundry status, upload, source
  filters, indexed-source summary, retry indexing, and model unload.
- Multiple files can be selected and processed sequentially. One failed file does not prevent later
  files from being processed.
- Session-only chat history stores safe message text, citations, status, timings, and warnings in
  `st.session_state`. It is not persisted to SQLite.
- English and Turkish UI text is centralized in `groundnote.ui.text`.
- Citations are compact in the chat view, with technical details hidden by default.

## Benchmarks

Automated fake-provider tests confirmed greeting routing without model calls and retrieval across
long and multiple documents. Full local tests passed with 191 non-Foundry tests and 80% total
coverage.

Real Foundry timings from the safe smoke fixture:

| Operation | Time |
| --- | ---: |
| Deterministic greeting | 0.07 ms |
| Index one Markdown fixture | 5.316 s |
| English grounded answer | 20.919 s |
| Turkish grounded answer | 12.946 s |
| Insufficient-evidence answer | 12.969 s |

These are machine-specific and use a tiny safe fixture. Phase 7.1 keeps the previous 73.93 s manual
observation as the baseline to beat during user testing with the real user document.

## Known Limitations

- Chat history is session-only and clears when the Streamlit session restarts.
- Retry indexing is intentionally minimal and does not replace Phase 8 Knowledge Base management.
- FTS5 fallback is vector-only if a SQLite runtime does not provide FTS5.
- Streaming is bounded by the currently installed Foundry Local provider behavior.

Phase 8 has not started.
