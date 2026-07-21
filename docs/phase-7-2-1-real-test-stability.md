# Phase 7.2.1 Real Test Stability

Phase 7.2.1 is a stabilization patch based on real UI testing with multiple study documents. It
does not start Phase 8 and does not add full Knowledge Base management.

## What Changed

- Added minimal confirmed document removal from the Streamlit document list.
- Added deterministic document inventory and grouping answers from indexed document metadata.
- Hid normal-flow technical/debug details behind a disabled-by-default settings toggle.
- Added operation guards so indexing and answer generation are not started on top of each other.
- Added modest model idle cleanup behavior:
  - Fast keeps models warm for about 5 minutes.
  - Balanced keeps models warm for about 2 minutes.
  - Memory saver unloads after each operation and also uses a short idle TTL.
- Increased the default answer token budget from 224 to 320 while strengthening concise-answer
  prompt instructions.
- Added local quality cleanup for answer headings, dangling endings, and table/numeric caution.
- Added evidence-gated deterministic answers for several simple real-test question shapes.

## Document Removal

The remove action deletes the selected document record and its local index rows from SQLite. It
does not delete the user's original file from disk and it does not remove other documents.

Deleted documents no longer appear in document inventory answers or retrieval results. Existing
session chat messages may remain as historical text, but future retrieval cannot use the deleted
document.

## Inventory And Grouping Questions

Questions such as "What documents are indexed?" and "Group the documents I uploaded" are treated as
application inventory questions. GroundNote answers from indexed document metadata instead of
retrieving arbitrary chunks from document content. These answers do not call the chat model and do
not fabricate page citations.

## Resource Control

GroundNote still runs synchronously and locally. It does not create a background queue. The UI
prevents overlapping heavy operations in the normal Streamlit flow, processes selected uploads
sequentially, and unloads chat models before starting document indexing.

Resource measurements are best-effort. GroundNote does not claim strict RAM or temperature caps
because Foundry Local and Windows resource behavior cannot be fully controlled from the app.

## Manual Smoke Notes

The requested real document set was not found under the repository, Downloads, or Documents search
locations during this patch. Representative local fixture smoke was used for document inventory,
delete, invalid/greeting bypasses, and the MB-like table caution path.

Measured representative local fixture timings:

| Operation | Time |
| --- | ---: |
| Inventory answer, English | 0.532 ms |
| Inventory answer, English repeated form | 0.434 ms |
| MB-like table caution answer | 2.932 ms |
| Delete old Phases fixture from index | 2.721 ms |

Real Foundry UI smoke with a temporary Markdown fixture passed after starting the local Foundry
server. Models were unloaded afterward and `foundry status` reported `Loaded 0`.

## Remaining Limitations

- Full Knowledge Base management, bulk delete, and re-index controls remain Phase 8.
- Large PDF indexing is still synchronous and CPU-bound.
- Local model wording and latency can vary.
- Messy PDF tables can remain ambiguous; GroundNote now prefers uncertainty over unsupported
  numeric claims.
- OCR is still not included in the MVP.
