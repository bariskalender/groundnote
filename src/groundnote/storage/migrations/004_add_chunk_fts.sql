CREATE VIRTUAL TABLE IF NOT EXISTS document_chunks_fts USING fts5(
    chunk_id UNINDEXED,
    document_id UNINDEXED,
    content,
    section_title,
    source_filename,
    tokenize='unicode61'
);

INSERT INTO document_chunks_fts (
    rowid,
    chunk_id,
    document_id,
    content,
    section_title,
    source_filename
)
SELECT
    c.rowid,
    c.id,
    c.document_id,
    c.content,
    COALESCE(c.section_title, ''),
    d.original_filename
FROM document_chunks c
JOIN documents d ON d.id = c.document_id
WHERE NOT EXISTS (
    SELECT 1
    FROM document_chunks_fts f
    WHERE f.chunk_id = c.id
);
