# Document Processing

Phase 3 adds the local document-processing foundation. It validates files, hashes original bytes,
checks for exact duplicates, selects a parser, extracts text, and returns parser-neutral models.

It does not create chunks, generate embeddings, index documents, retrieve context, call Foundry
Local models, or generate RAG answers.

## Processing Flow

1. Validate the path and filename.
2. Detect the supported file type from the extension.
3. Enforce the configured upload size limit.
4. Check basic content signatures and binary-looking text files.
5. Calculate a streaming SHA-256 hash from original file bytes.
6. Check the existing document repository for an exact SHA-256 duplicate.
7. Select the parser from the parser registry.
8. Parse into `ParsedDocument` and `ParsedSection` models.
9. Log only safe metadata and timings.

## Hashing And Duplicate Pre-Check

SHA-256 is calculated from original bytes in chunks. The duplicate pre-check queries
`DocumentRepository.get_by_sha256()` before expensive parsing. Exact duplicates are reported, but
Phase 3 does not delete, replace, or re-index existing documents.

## Parser Registry

The registry maps `SupportedFileType` values to parser implementations. Missing parsers fail with
a clear application-specific error. The registry is independent of Streamlit and SQLite.

## Parser Behavior

- PDF: extracts text page by page, stores 1-based page numbers, rejects encrypted/corrupted files,
  and reports scanned/image-only limitations.
- DOCX: extracts headings, paragraphs, list text, and simple table text; page numbers remain null.
- TXT: decodes UTF-8 or UTF-8 with BOM and rejects binary-looking files.
- Markdown: splits by headings while preserving lists, code blocks, inline text, and inert HTML.

## Normalization

Text normalization is conservative. It normalizes line endings, removes null bytes, trims excessive
blank lines, and collapses repeated horizontal spaces outside code-like content. It preserves
Unicode, Turkish characters, mathematical symbols, code blocks, punctuation, and casing.

## Error Handling

Document errors are application-specific and user-safe. They do not expose absolute paths, parser
library stack traces, raw bytes, or document contents.

## Privacy

Document processing is local. Logs include safe metadata such as filename, file type, size, parser
name, section count, page count, warning count, timing, and failure category. Logs do not include
full document text, extracted sections, raw bytes, absolute paths, or full hashes.

## Current Limitations

- No OCR.
- No persistent ingestion workflow.
- No chunking.
- No embedding generation.
- No semantic retrieval.
- No RAG answer generation.
- No final upload or chat UI.
