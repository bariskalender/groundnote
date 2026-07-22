# Phase 9.1C Multi-file Upload Queue

## Scope and ownership

GroundNote accepts PDF, DOCX, TXT, and Markdown files as one bounded selection. The Streamlit
session owns the queue; there is no background daemon, task worker, parallel indexing, or durable
job queue. The default limits are 10 files, 50 MB per file, and 100 MB combined.

Each submission and queue item has an opaque stable identity. Queue metadata contains only a
sanitized filename, type, byte size, SHA-256 content fingerprint, sequence/timestamp, current stage,
real progress counters, safe outcome, duration, document ID when persisted, and retry availability.
It never stores extracted text, embeddings, prompts, paths, or raw exceptions.

## Sequential lifecycle

The queue uses these UI states without changing database status meanings:

`Waiting → Validating → Parsing → Chunking → Embedding → Saving → Verifying → Ready`

Duplicate, Failed, Interrupted, and Cancelled are terminal queue outcomes. Exactly one item may be
active. Duplicate, invalid, parser, embedding, and persistence failures affect only that item and
the next Waiting item continues. One global operation guard blocks chat until every selected item
has a terminal outcome.

Waiting items own one bounded immutable byte buffer. Success, duplicate, failure, interruption, or
cancellation releases it immediately. The embedding model is reused between queue items and all
GroundNote-owned models are unloaded in final cleanup, including middle- and final-failure paths.

## Retry, cancellation, and reruns

- A persisted Failed or Interrupted document can be retried through the existing Phase 9.1A
  re-index and integrity contract.
- A failure before database persistence releases its bytes and requires file reselection.
- Duplicate items do not offer queue Retry; explicit Knowledge Base Re-index remains available.
- A Waiting item may be cancelled without changing an active item. Active work is not cancelled.
- Ordinary reruns, language/debug changes, New Chat, flash messages, and uploader resets do not
  repeat active or completed work.
- A full browser session refresh may lose Waiting files. GroundNote does not resume incomplete
  buffers; the user must select them again. Database recovery remains authoritative for persisted
  interrupted work.

## Measured isolated result

On 2026-07-22, the real Foundry Local benchmark used three generated 2,588-byte files and the cached
`qwen3-embedding-0.6b` CPU model:

| File | Chunks | Duration | Model reused |
| --- | ---: | ---: | --- |
| `queue-fixture-1.txt` | 3 | 5.055 s | No |
| `queue-fixture-2.md` | 13 | 6.893 s | Yes |
| `queue-fixture-3.txt` | 3 | 2.812 s | Yes |

- Queue total: 14.761 s.
- Maximum simultaneous indexing items: 1.
- Peak GroundNote process RSS observed: 906.695 MB.
- Peak retained upload buffers: 7,764 bytes; final retained bytes: 0.
- Loaded model count: 0 before, 1 after the queue, and 0 after cleanup.
- Outcomes: 3 Ready, 0 Duplicate, 0 Failed; cleanup warnings: 0.

These are measurements from generated fixtures on the current Windows machine, not performance
guarantees for arbitrary documents.

## Deferred work

Phase 9.1D security and release hardening remains unstarted. Phase 10 has not started. Persistent
queues, parallel indexing, active-operation cancellation, cloud services, OCR, and model changes are
outside this phase.
