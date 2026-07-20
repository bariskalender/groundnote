# Supported Documents

GroundNote supports safe validation and text extraction for small to medium local study documents.
Ingestion, chunking, embeddings, retrieval, and grounded RAG answers live in later architecture
layers.

## Supported Extensions

- PDF: `.pdf`
- DOCX: `.docx`
- Plain text: `.txt`
- Markdown: `.md`, `.markdown`

Extensions are checked case-insensitively. Browser MIME types are not trusted as the only signal.

## File Size Limit

The upload size limit is controlled by `GROUNDNOTE_MAX_UPLOAD_MB`, which defaults to `50`.

## PDF Limits

PDF text is extracted page by page with 1-based page numbers. Blank pages are recorded as
warnings. Encrypted PDFs are rejected. Corrupted PDFs are rejected with a safe user-facing error.

OCR is not supported. Scanned or image-only PDFs may fail with a message explaining that no
readable text could be extracted.

## DOCX Limits

DOCX files are read as document content only. GroundNote extracts paragraphs, heading text, list
text, and simple table text. It does not execute macros, follow links, load external references, or
render page layout. DOCX page numbers are unavailable because they depend on layout rendering.

## TXT And Markdown Encoding

TXT and Markdown files are decoded as UTF-8, including UTF-8 with BOM. Binary-looking text files
are rejected instead of being decoded as arbitrary data.

Markdown is treated as inert text. HTML, JavaScript, links, images, and embedded content are not
executed or fetched.

## Safe Upload Expectations

GroundNote normalizes display filenames, rejects traversal attempts, and generates UUID-prefixed
stored filenames to avoid overwrites. Uploaded bytes should be written only into an
application-controlled document directory.

Do not commit uploaded documents to Git.
