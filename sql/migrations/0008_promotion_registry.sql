-- 0008_promotion_registry.sql: Promotion Registry append-only tables and state machine checks.

CREATE TABLE IF NOT EXISTS model_promotion_record (
    promotion_event_id TEXT PRIMARY KEY,
    model_artifact_id TEXT NOT NULL,
    promotion_state TEXT NOT NULL CHECK (promotion_state IN (
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
    target_stage TEXT NOT NULL CHECK (target_stage IN ('RESEARCH', 'PAPER', 'LIVE')),
    experiment_fingerprint TEXT NOT NULL,
    dataset_ids_json TEXT NOT NULL,
    universe_ids_json TEXT NOT NULL,
    code_commit TEXT NOT NULL,
    config_version TEXT NOT NULL,
    feature_version TEXT NOT NULL,
    representation_version TEXT NOT NULL,
    portfolio_version TEXT NOT NULL,
    cost_model_version TEXT NOT NULL,
    risk_policy_version TEXT NOT NULL,
    effective_time TEXT NOT NULL,
    approving_authority TEXT NOT NULL,
    evidence_reference TEXT NOT NULL,
    paper_observation_reference TEXT,
    kill_switch_procedure TEXT,
    event_at TEXT NOT NULL,
    reason TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_promotion_artifact_event
    ON model_promotion_record(model_artifact_id, event_at);

CREATE INDEX IF NOT EXISTS idx_promotion_state
    ON model_promotion_record(promotion_state);
