PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS source (
    source_id TEXT PRIMARY KEY,
    source_type TEXT NOT NULL,
    official_url TEXT,
    terms_class TEXT,
    config_json TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS raw_object (
    raw_object_id TEXT PRIMARY KEY,
    source_id TEXT NOT NULL REFERENCES source(source_id),
    sha256 TEXT NOT NULL UNIQUE,
    byte_size INTEGER NOT NULL CHECK (byte_size >= 0),
    storage_uri TEXT NOT NULL UNIQUE,
    original_name TEXT,
    request_json TEXT,
    response_metadata_json TEXT,
    source_checksum TEXT,
    acquired_at TEXT NOT NULL,
    event_start TEXT,
    event_end TEXT,
    status TEXT NOT NULL,
    UNIQUE(source_id, sha256)
);

CREATE TABLE IF NOT EXISTS dataset (
    dataset_id TEXT PRIMARY KEY,
    dataset_type TEXT NOT NULL,
    schema_version TEXT NOT NULL,
    manifest_sha256 TEXT NOT NULL UNIQUE,
    manifest_uri TEXT NOT NULL UNIQUE,
    transform_name TEXT NOT NULL,
    transform_version TEXT NOT NULL,
    code_commit TEXT NOT NULL,
    config_sha256 TEXT NOT NULL,
    row_count INTEGER NOT NULL CHECK (row_count >= 0),
    byte_size INTEGER NOT NULL CHECK (byte_size >= 0),
    event_start TEXT,
    event_end TEXT,
    availability_start TEXT,
    availability_end TEXT,
    quality_status TEXT NOT NULL,
    supersedes_dataset_id TEXT REFERENCES dataset(dataset_id),
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS dataset_input_dataset (
    dataset_id TEXT NOT NULL REFERENCES dataset(dataset_id),
    input_dataset_id TEXT NOT NULL REFERENCES dataset(dataset_id),
    role TEXT NOT NULL,
    PRIMARY KEY (dataset_id, input_dataset_id, role),
    CHECK (dataset_id <> input_dataset_id)
);

CREATE TABLE IF NOT EXISTS dataset_input_raw_object (
    dataset_id TEXT NOT NULL REFERENCES dataset(dataset_id),
    raw_object_id TEXT NOT NULL REFERENCES raw_object(raw_object_id),
    role TEXT NOT NULL,
    PRIMARY KEY (dataset_id, raw_object_id, role)
);

CREATE TABLE IF NOT EXISTS dataset_file (
    dataset_id TEXT NOT NULL REFERENCES dataset(dataset_id),
    file_sha256 TEXT NOT NULL,
    storage_uri TEXT NOT NULL,
    row_count INTEGER NOT NULL CHECK (row_count >= 0),
    byte_size INTEGER NOT NULL CHECK (byte_size >= 0),
    partition_json TEXT,
    PRIMARY KEY (dataset_id, file_sha256),
    UNIQUE (dataset_id, storage_uri)
);

CREATE TABLE IF NOT EXISTS watermark (
    source_id TEXT NOT NULL REFERENCES source(source_id),
    stream_key TEXT NOT NULL,
    last_complete_event_time TEXT,
    cursor_json TEXT,
    updated_at TEXT NOT NULL,
    PRIMARY KEY (source_id, stream_key)
);

CREATE TABLE IF NOT EXISTS build_run (
    run_id TEXT PRIMARY KEY,
    command TEXT NOT NULL,
    code_commit TEXT NOT NULL,
    config_sha256 TEXT NOT NULL,
    started_at TEXT NOT NULL,
    ended_at TEXT,
    status TEXT NOT NULL,
    output_dataset_id TEXT REFERENCES dataset(dataset_id),
    metrics_json TEXT,
    error_json TEXT
);

CREATE TABLE IF NOT EXISTS quality_issue (
    issue_id TEXT PRIMARY KEY,
    rule_id TEXT NOT NULL,
    rule_version TEXT NOT NULL,
    severity TEXT NOT NULL,
    raw_object_id TEXT REFERENCES raw_object(raw_object_id),
    dataset_id TEXT REFERENCES dataset(dataset_id),
    instrument_id INTEGER,
    event_start TEXT,
    event_end TEXT,
    details_json TEXT NOT NULL,
    status TEXT NOT NULL,
    resolution_json TEXT,
    created_at TEXT NOT NULL,
    resolved_at TEXT,
    CHECK (raw_object_id IS NOT NULL OR dataset_id IS NOT NULL)
);

CREATE TABLE IF NOT EXISTS experiment_spec (
    fingerprint TEXT PRIMARY KEY,
    experiment_id TEXT NOT NULL,
    research_mode TEXT NOT NULL,
    code_commit TEXT NOT NULL,
    lock_sha256 TEXT NOT NULL,
    config_sha256 TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS experiment_input_dataset (
    fingerprint TEXT NOT NULL REFERENCES experiment_spec(fingerprint),
    dataset_id TEXT NOT NULL REFERENCES dataset(dataset_id),
    role TEXT NOT NULL,
    PRIMARY KEY (fingerprint, dataset_id, role)
);

CREATE TABLE IF NOT EXISTS experiment_run (
    run_id TEXT PRIMARY KEY,
    fingerprint TEXT NOT NULL REFERENCES experiment_spec(fingerprint),
    attempt INTEGER NOT NULL CHECK (attempt >= 1),
    bundle_uri TEXT,
    status TEXT NOT NULL,
    decision TEXT NOT NULL,
    started_at TEXT NOT NULL,
    ended_at TEXT,
    error_json TEXT,
    UNIQUE (fingerprint, attempt),
    UNIQUE (bundle_uri)
);

CREATE TABLE IF NOT EXISTS model_artifact (
    model_artifact_id TEXT PRIMARY KEY,
    fingerprint TEXT NOT NULL REFERENCES experiment_spec(fingerprint),
    artifact_sha256 TEXT NOT NULL UNIQUE,
    artifact_uri TEXT NOT NULL UNIQUE,
    manifest_uri TEXT NOT NULL UNIQUE,
    representation_type TEXT NOT NULL,
    representation_version TEXT NOT NULL,
    status TEXT NOT NULL
        CHECK (status IN (
            'RESEARCH_CANDIDATE',
            'RESEARCH_ACCEPTED',
            'PAPER_APPROVED',
            'PAPER_SUSPENDED',
            'LIVE_APPROVED',
            'LIVE_SUSPENDED',
            'RETIRED',
            'REJECTED',
            'QUARANTINED'
        )),
    created_at TEXT NOT NULL
);

-- Append-only promotion history. The current stage target is the latest event per stage.
-- Aligned with ADR-0008 (Research, Paper, Live promotion lifecycle). Each event pins the
-- exact immutable identity of the promoted artifact and the authorizing authority; a new
-- artifact version does not inherit a prior version's authorization.
CREATE TABLE IF NOT EXISTS model_promotion_event (
    promotion_event_id TEXT PRIMARY KEY,
    stage TEXT NOT NULL CHECK (stage IN ('RESEARCH', 'PAPER', 'LIVE')),
    action TEXT NOT NULL CHECK (action IN ('PROMOTE', 'SUSPEND', 'RESUME', 'RETIRE', 'REJECT', 'QUARANTINE')),
    promotion_state TEXT NOT NULL
        CHECK (promotion_state IN (
            'RESEARCH_CANDIDATE',
            'RESEARCH_ACCEPTED',
            'PAPER_APPROVED',
            'PAPER_SUSPENDED',
            'LIVE_APPROVED',
            'LIVE_SUSPENDED',
            'RETIRED',
            'REJECTED',
            'QUARANTINED'
        )),
    model_artifact_id TEXT REFERENCES model_artifact(model_artifact_id),
    experiment_fingerprint TEXT NOT NULL,
    dataset_ids_json TEXT NOT NULL,
    universe_version TEXT NOT NULL,
    code_commit TEXT NOT NULL,
    config_sha256 TEXT NOT NULL,
    feature_version TEXT NOT NULL,
    representation_version TEXT NOT NULL,
    portfolio_version TEXT NOT NULL,
    cost_model_version TEXT NOT NULL,
    risk_policy_version TEXT NOT NULL,
    effective_time TEXT NOT NULL,
    approving_authority TEXT NOT NULL,
    evidence_ref TEXT NOT NULL,
    event_at TEXT NOT NULL,
    actor TEXT NOT NULL,
    reason TEXT NOT NULL,
    CHECK (
        (action IN ('PROMOTE', 'SUSPEND', 'RESUME', 'RETIRE', 'REJECT', 'QUARANTINE')
            AND model_artifact_id IS NOT NULL)
    )
);

CREATE INDEX IF NOT EXISTS idx_raw_object_source_acquired
    ON raw_object(source_id, acquired_at);
CREATE INDEX IF NOT EXISTS idx_dataset_type_created
    ON dataset(dataset_type, created_at);
CREATE INDEX IF NOT EXISTS idx_quality_issue_status
    ON quality_issue(status, severity);
CREATE INDEX IF NOT EXISTS idx_experiment_run_fingerprint
    ON experiment_run(fingerprint, attempt);
CREATE INDEX IF NOT EXISTS idx_model_promotion_stage_time
    ON model_promotion_event(stage, event_at);
