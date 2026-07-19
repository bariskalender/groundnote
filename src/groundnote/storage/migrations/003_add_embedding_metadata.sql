ALTER TABLE documents
ADD COLUMN embedding_version TEXT NULL;

ALTER TABLE document_chunks
ADD COLUMN embedding_model TEXT NULL;

ALTER TABLE document_chunks
ADD COLUMN embedding_version TEXT NULL;

ALTER TABLE document_chunks
ADD COLUMN embedded_at TEXT NULL;

CREATE INDEX idx_document_chunks_embedding_model
ON document_chunks(embedding_model, embedding_version);
