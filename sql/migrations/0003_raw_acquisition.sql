-- RAW-001: acquisition provenance ledger separate from content-addressed raw_object.
-- Additive only. Existing raw_object rows are unchanged; new code records provenance here.

PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS raw_acquisition (
    acquisition_id TEXT PRIMARY KEY,
    source_id TEXT NOT NULL REFERENCES source(source_id),
    raw_object_id TEXT REFERENCES raw_object(raw_object_id),
    request_json TEXT NOT NULL,
    response_metadata_json TEXT NOT NULL,
    original_name TEXT,
    checksum_algorithm TEXT,
    checksum_value TEXT,
    checksum_verification TEXT NOT NULL
        CHECK (checksum_verification IN (
            'absent',
            'verified',
            'mismatch',
            'unsupported',
            'malformed',
            'failed'
        )),
    acquired_at TEXT NOT NULL,
    event_start TEXT,
    event_end TEXT,
    status TEXT NOT NULL
        CHECK (status IN (
            'SUCCEEDED',
            'FAILED',
            'REGISTRATION_PENDING',
            'REJECTED'
        )),
    failure_json TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    CHECK (
        (status = 'SUCCEEDED' AND raw_object_id IS NOT NULL)
        OR (status IN ('FAILED', 'REJECTED') AND raw_object_id IS NULL)
        OR (status = 'REGISTRATION_PENDING')
    )
);

CREATE INDEX IF NOT EXISTS idx_raw_acquisition_source_acquired
    ON raw_acquisition(source_id, acquired_at);

CREATE INDEX IF NOT EXISTS idx_raw_acquisition_raw_object
    ON raw_acquisition(raw_object_id);

CREATE INDEX IF NOT EXISTS idx_raw_acquisition_status
    ON raw_acquisition(status, acquired_at);
