ALTER TABLE document_chunks
ADD COLUMN source_start_order INTEGER NULL CHECK (
    source_start_order IS NULL OR source_start_order >= 0
);

ALTER TABLE document_chunks
ADD COLUMN source_end_order INTEGER NULL CHECK (
    source_end_order IS NULL OR source_end_order >= 0
);

ALTER TABLE document_chunks
ADD COLUMN chunking_version TEXT NULL;

ALTER TABLE document_chunks
ADD COLUMN metadata_json TEXT NULL;
