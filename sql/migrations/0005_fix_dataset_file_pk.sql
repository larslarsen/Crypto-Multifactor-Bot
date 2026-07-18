-- MAN-001: Change dataset_file PK to (dataset_id, storage_uri)
-- Duplicate content at different logical paths is now allowed; identity is the
-- storage_uri (logical path), not the content hash. Preserve all data, FK, and
-- the partition_json column. Runner owns the surrounding transaction.

CREATE TABLE dataset_file_new (
    dataset_id TEXT NOT NULL,
    storage_uri TEXT NOT NULL,
    file_sha256 TEXT NOT NULL,
    byte_size INTEGER NOT NULL CHECK (byte_size >= 0),
    row_count INTEGER NOT NULL CHECK (row_count >= 0),
    partition_json TEXT,
    FOREIGN KEY (dataset_id) REFERENCES dataset(dataset_id),
    PRIMARY KEY (dataset_id, storage_uri)
);

INSERT INTO dataset_file_new (
    dataset_id, storage_uri, file_sha256, byte_size, row_count, partition_json
)
SELECT dataset_id, storage_uri, file_sha256, byte_size, row_count, partition_json
FROM dataset_file;

DROP TABLE dataset_file;
ALTER TABLE dataset_file_new RENAME TO dataset_file;

CREATE INDEX idx_dataset_file_sha256 ON dataset_file(file_sha256);
