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

The per-file upload size limit is controlled by `GROUNDNOTE_MAXIMUM_UPLOAD_SIZE_MB`, which defaults
to `50`.
GroundNote accepts one document at a time. It does not retain additional uploads in a background
or browser-session queue.

The compressed upload limit is only the first guard. GroundNote also defaults to at most
`5,000,000` extracted characters and `10,000` searchable chunks per document. These limits are
checked before local embedding, so an oversized document cannot become Ready or leave a usable
partial index.

## PDF Limits

PDF text is extracted page by page with 1-based page numbers. Blank pages are recorded as
warnings. Encrypted PDFs are rejected. Corrupted PDFs are rejected with a safe user-facing error.
GroundNote reads the PDF page count before page extraction and rejects documents over `1,000`
pages. The cumulative extracted-character limit is checked after every page, and parser file
handles are closed on both success and failure.

OCR is not supported. Scanned or image-only PDFs may fail with a message explaining that no
readable text could be extracted.

## DOCX Limits

DOCX files are treated as untrusted ZIP archives. Before reading document XML, GroundNote rejects
encrypted, absolute, traversal, duplicate, symlink-like, special, malformed, or excessive archive
members. Default bounds are `2,000` members, `200 MB` total declared expansion, `50 MB` per member,
and a `100:1` per-member and total compression ratio. Only `word/document.xml` and optional
`word/styles.xml` are read through bounded streams; embedded media and unrelated package parts are
not extracted to disk.

GroundNote extracts paragraphs, heading text, list text, and simple table text. It does not execute
macros, follow links, load external references, or render page layout. DOCX page numbers are
unavailable because they depend on layout rendering.

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
