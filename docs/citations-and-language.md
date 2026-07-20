# Citations And Language

GroundNote citations are based on trusted retrieval metadata, not model-generated filenames or page
numbers.

## Inline Syntax

The model is instructed to cite with source IDs such as `[S1]` or `[S1][S2]`. After generation,
GroundNote extracts only allowed citation IDs. Unknown IDs are removed or rejected and never become
trusted citations.

If citations are required and the first generated answer contains no valid citations, GroundNote
performs at most one citation-repair generation. If that also fails, the service returns a safe
citation validation error instead of inventing sources.

## Display Labels

- PDF: `filename.pdf — page 3`
- DOCX: `filename.docx — Section Title`
- Markdown: `notes.md — Section Title`
- TXT: `notes.txt — chunk 4`
- Fallback: filename only

Filenames are reduced to safe display names. Stored UUID filenames and absolute paths are not shown.
PDF page numbers remain 1-based.

## Language Handling

Supported response language values are `tr`, `en`, and `auto`.

- Explicit `tr` or `en` wins.
- `auto` uses a lightweight deterministic heuristic.
- Turkish-specific characters strongly indicate Turkish.
- Turkish and English marker words are compared when possible.
- Uncertain input defaults to English.

Document language does not override the user's question language. Filenames and source titles are
preserved instead of translated.

This heuristic is intentionally lightweight and does not claim perfect language identification.
