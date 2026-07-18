-- MAN-001: additive dataset publication state and schema fingerprint columns.
PRAGMA foreign_keys = ON;

-- publication_status: REGISTERED (accepted in catalog), SUPERSEDED (optional marker).
ALTER TABLE dataset ADD COLUMN publication_status TEXT NOT NULL DEFAULT 'REGISTERED';

ALTER TABLE dataset ADD COLUMN schema_fingerprint TEXT;

ALTER TABLE dataset ADD COLUMN quality_summary_json TEXT;

ALTER TABLE dataset ADD COLUMN publication_uri TEXT;

CREATE INDEX IF NOT EXISTS idx_dataset_publication_status
    ON dataset(publication_status, created_at);

CREATE INDEX IF NOT EXISTS idx_dataset_schema_fingerprint
    ON dataset(schema_fingerprint);
