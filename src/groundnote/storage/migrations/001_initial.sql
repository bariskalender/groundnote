CREATE TABLE documents (
    id TEXT PRIMARY KEY,
    original_filename TEXT NOT NULL,
    stored_filename TEXT NOT NULL,
    file_type TEXT NOT NULL CHECK (file_type IN ('pdf', 'docx', 'txt', 'markdown')),
    sha256 TEXT NOT NULL UNIQUE,
    file_size_bytes INTEGER NOT NULL CHECK (file_size_bytes >= 0),
    page_count INTEGER NULL CHECK (page_count IS NULL OR page_count > 0),
    status TEXT NOT NULL CHECK (
        status IN (
            'pending',
            'parsing',
            'parsed',
            'pending_embedding',
            'indexing',
            'indexed',
            'failed',
            'incompatible_index'
        )
    ),
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    indexed_at TEXT NULL,
    error_message TEXT NULL,
    embedding_model TEXT NULL,
    embedding_dimension INTEGER NULL CHECK (
        embedding_dimension IS NULL OR embedding_dimension > 0
    ),
    chunking_version TEXT NULL
);

CREATE TABLE document_chunks (
    id TEXT PRIMARY KEY,
    document_id TEXT NOT NULL,
    chunk_index INTEGER NOT NULL CHECK (chunk_index >= 0),
    content TEXT NOT NULL,
    page_number INTEGER NULL CHECK (page_number IS NULL OR page_number > 0),
    section_title TEXT NULL,
    character_count INTEGER NOT NULL CHECK (character_count >= 0),
    token_estimate INTEGER NULL CHECK (token_estimate IS NULL OR token_estimate >= 0),
    embedding BLOB NULL,
    embedding_dimension INTEGER NULL CHECK (
        embedding_dimension IS NULL OR embedding_dimension > 0
    ),
    embedding_dtype TEXT NULL CHECK (embedding_dtype IS NULL OR embedding_dtype = 'float32'),
    created_at TEXT NOT NULL,
    FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE CASCADE,
    UNIQUE (document_id, chunk_index)
);

CREATE TABLE application_metadata (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE INDEX idx_documents_sha256 ON documents(sha256);
CREATE INDEX idx_documents_status ON documents(status);
CREATE INDEX idx_documents_indexed_at ON documents(indexed_at);
CREATE INDEX idx_document_chunks_document_id ON document_chunks(document_id);
