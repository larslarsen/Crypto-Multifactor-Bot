PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS hypothesis (
    hypothesis_id TEXT PRIMARY KEY,
    slug TEXT NOT NULL UNIQUE,
    created_at TEXT NOT NULL,
    created_by TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS hypothesis_version (
    hypothesis_id TEXT NOT NULL REFERENCES hypothesis(hypothesis_id),
    version INTEGER NOT NULL CHECK (version >= 1),
    title TEXT NOT NULL,
    statement TEXT NOT NULL,
    mechanism TEXT NOT NULL,
    expected_sign TEXT NOT NULL,
    phase TEXT NOT NULL,
    primary_metric TEXT NOT NULL,
    advancement_rule TEXT NOT NULL,
    rejection_rule TEXT NOT NULL,
    details_json TEXT NOT NULL,
    content_sha256 TEXT NOT NULL UNIQUE,
    preregistered_at TEXT,
    created_at TEXT NOT NULL,
    created_by TEXT NOT NULL,
    PRIMARY KEY (hypothesis_id, version)
);

CREATE TABLE IF NOT EXISTS evidence_item (
    evidence_id TEXT PRIMARY KEY,
    kind TEXT NOT NULL CHECK (kind IN (
        'LITERATURE_PUBLISHED', 'LITERATURE_WORKING', 'LEGACY_RESULT',
        'EXPERIMENT_RESULT', 'DATA_AUDIT', 'THEORY', 'OPERATIONAL_OBSERVATION'
    )),
    title TEXT NOT NULL,
    summary TEXT NOT NULL,
    source_ref TEXT NOT NULL,
    artifact_uri TEXT,
    observed_at TEXT,
    registered_at TEXT NOT NULL,
    registered_by TEXT NOT NULL,
    content_sha256 TEXT NOT NULL UNIQUE,
    metadata_json TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS hypothesis_evidence_link (
    hypothesis_id TEXT NOT NULL,
    hypothesis_version INTEGER NOT NULL,
    evidence_id TEXT NOT NULL REFERENCES evidence_item(evidence_id),
    direction TEXT NOT NULL CHECK (direction IN ('SUPPORTS', 'CONTRADICTS', 'QUALIFIES', 'NEUTRAL')),
    relevance TEXT NOT NULL CHECK (relevance IN ('PRIMARY', 'SECONDARY', 'CONTEXT')),
    rationale TEXT NOT NULL,
    integrity_json TEXT NOT NULL,
    registered_at TEXT NOT NULL,
    registered_by TEXT NOT NULL,
    PRIMARY KEY (hypothesis_id, hypothesis_version, evidence_id),
    FOREIGN KEY (hypothesis_id, hypothesis_version)
        REFERENCES hypothesis_version(hypothesis_id, version)
);

CREATE TABLE IF NOT EXISTS hypothesis_experiment_link (
    hypothesis_id TEXT NOT NULL,
    hypothesis_version INTEGER NOT NULL,
    experiment_fingerprint TEXT NOT NULL REFERENCES experiment_spec(fingerprint),
    role TEXT NOT NULL CHECK (role IN ('PRIMARY_TEST', 'REPLICATION', 'ROBUSTNESS', 'ABLATION', 'DIAGNOSTIC')),
    registered_at TEXT NOT NULL,
    PRIMARY KEY (hypothesis_id, hypothesis_version, experiment_fingerprint, role),
    FOREIGN KEY (hypothesis_id, hypothesis_version)
        REFERENCES hypothesis_version(hypothesis_id, version)
);

CREATE TABLE IF NOT EXISTS evidence_snapshot (
    snapshot_id TEXT PRIMARY KEY,
    hypothesis_id TEXT NOT NULL,
    hypothesis_version INTEGER NOT NULL,
    as_of TEXT NOT NULL,
    generated_at TEXT NOT NULL,
    content_sha256 TEXT NOT NULL UNIQUE,
    artifact_uri TEXT,
    snapshot_json TEXT NOT NULL,
    FOREIGN KEY (hypothesis_id, hypothesis_version)
        REFERENCES hypothesis_version(hypothesis_id, version)
);

CREATE TABLE IF NOT EXISTS hypothesis_decision_event (
    decision_id TEXT PRIMARY KEY,
    hypothesis_id TEXT NOT NULL,
    hypothesis_version INTEGER NOT NULL,
    action TEXT NOT NULL CHECK (action IN ('REGISTER', 'SET_VERDICT', 'DEFER', 'REOPEN', 'CLOSE', 'CORRECT')),
    lifecycle TEXT NOT NULL CHECK (lifecycle IN ('DRAFT', 'REGISTERED', 'ACTIVE', 'DEFERRED', 'CLOSED')),
    verdict TEXT NOT NULL CHECK (verdict IN (
        'UNTESTED', 'PRELIMINARY', 'SUPPORTED', 'REPLICATED', 'NOT_REPLICATED',
        'REJECTED', 'INCONCLUSIVE', 'QUARANTINED'
    )),
    evidence_snapshot_id TEXT NOT NULL REFERENCES evidence_snapshot(snapshot_id),
    reason TEXT NOT NULL,
    actor TEXT NOT NULL,
    event_at TEXT NOT NULL,
    supersedes_decision_id TEXT REFERENCES hypothesis_decision_event(decision_id),
    FOREIGN KEY (hypothesis_id, hypothesis_version)
        REFERENCES hypothesis_version(hypothesis_id, version)
);

CREATE INDEX IF NOT EXISTS idx_hypothesis_version_created
    ON hypothesis_version(hypothesis_id, version);
CREATE INDEX IF NOT EXISTS idx_evidence_kind_registered
    ON evidence_item(kind, registered_at);
CREATE INDEX IF NOT EXISTS idx_evidence_link_hypothesis
    ON hypothesis_evidence_link(hypothesis_id, hypothesis_version, direction);
CREATE INDEX IF NOT EXISTS idx_hypothesis_decision_time
    ON hypothesis_decision_event(hypothesis_id, event_at, decision_id);
