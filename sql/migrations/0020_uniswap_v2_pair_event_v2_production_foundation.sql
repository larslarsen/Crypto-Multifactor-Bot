-- DEX-003 / ADR-0015 §9.10: production-path foundation (additive only).
--
-- Forward-only. Does NOT rebuild or weaken any 0017-0019 table.
-- Adds:
--   * root manifest (READY gate for production init)
--   * immutable reconciled-log candidate + required-block rows
--   * covering indexes for domain_id hash-order claims and candidate/header work
--
-- All new child FKs use exact plan/node/raw composite pairing where applicable.

-- ---------------------------------------------------------------------------
-- Root manifest: one row per plan; READY only after exact root set authenticates
-- ---------------------------------------------------------------------------
CREATE TABLE uniswap_v2_pair_event_v2_root_manifest (
    plan_id TEXT PRIMARY KEY,
    registry_dataset_id TEXT NOT NULL,
    registry_parquet_sha256 TEXT NOT NULL
        CHECK (length(registry_parquet_sha256) = 64),
    registry_parquet_bytes INTEGER NOT NULL
        CHECK (registry_parquet_bytes > 0),
    root_count INTEGER NOT NULL
        CHECK (root_count > 0),
    root_domain_set_sha256 TEXT NOT NULL
        CHECK (length(root_domain_set_sha256) = 64),
    pool_topic_blocks INTEGER NOT NULL
        CHECK (pool_topic_blocks > 0),
    status TEXT NOT NULL
        CHECK (status IN ('INITIALIZING', 'READY')),
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (plan_id) REFERENCES uniswap_v2_pair_event_v2_plan (plan_id)
        ON DELETE CASCADE ON UPDATE RESTRICT,
    CHECK (plan_id LIKE 'plan\_%' ESCAPE '\'),
    CHECK (
        registry_dataset_id =
        'ds_42ce2515e226258557a06a374498547393bbc984db791c56fa19d81d7ef16d15'
    )
);

CREATE INDEX idx_uniswap_v2_pair_event_v2_root_manifest_status
    ON uniswap_v2_pair_event_v2_root_manifest (status);

-- ---------------------------------------------------------------------------
-- Reconciled log candidate: dual logs retained + reconciled; zero coverage
-- ---------------------------------------------------------------------------
CREATE TABLE uniswap_v2_pair_event_v2_log_candidate (
    candidate_id TEXT PRIMARY KEY
        CHECK (candidate_id LIKE 'lcand\_%' ESCAPE '\'),
    plan_id TEXT NOT NULL,
    domain_id TEXT NOT NULL,
    attempt INTEGER NOT NULL CHECK (attempt >= 0),
    log_identity_sha256 TEXT NOT NULL
        CHECK (length(log_identity_sha256) = 64),
    log_count INTEGER NOT NULL CHECK (log_count >= 0),
    primary_provider_org TEXT NOT NULL,
    secondary_provider_org TEXT NOT NULL,
    primary_logs_raw_object_id TEXT NOT NULL
        CHECK (primary_logs_raw_object_id LIKE 'raw\_%' ESCAPE '\'),
    secondary_logs_raw_object_id TEXT NOT NULL
        CHECK (secondary_logs_raw_object_id LIKE 'raw\_%' ESCAPE '\'),
    primary_logs_acquisition_id TEXT NOT NULL
        CHECK (primary_logs_acquisition_id LIKE 'acq\_%' ESCAPE '\'),
    secondary_logs_acquisition_id TEXT NOT NULL
        CHECK (secondary_logs_acquisition_id LIKE 'acq\_%' ESCAPE '\'),
    request_json TEXT NOT NULL,
    created_at TEXT NOT NULL,
    -- Current plan resume generation that last raw-replayed this candidate.
    -- NULL / stale generation => not authoritative for claim exclusion.
    -- One integer per candidate row (no per-session row growth).
    session_auth_generation INTEGER
        CHECK (
            session_auth_generation IS NULL
            OR session_auth_generation >= 1
        ),
    UNIQUE (plan_id, domain_id),
    FOREIGN KEY (plan_id) REFERENCES uniswap_v2_pair_event_v2_plan (plan_id)
        ON DELETE CASCADE ON UPDATE RESTRICT,
    FOREIGN KEY (plan_id, domain_id)
        REFERENCES uniswap_v2_pair_event_v2_query_node (plan_id, domain_id)
        ON DELETE RESTRICT ON UPDATE RESTRICT,
    FOREIGN KEY (primary_logs_acquisition_id, primary_logs_raw_object_id)
        REFERENCES raw_acquisition (acquisition_id, raw_object_id)
        ON DELETE RESTRICT ON UPDATE RESTRICT,
    FOREIGN KEY (secondary_logs_acquisition_id, secondary_logs_raw_object_id)
        REFERENCES raw_acquisition (acquisition_id, raw_object_id)
        ON DELETE RESTRICT ON UPDATE RESTRICT,
    CHECK (plan_id LIKE 'plan\_%' ESCAPE '\'),
    CHECK (domain_id LIKE 'qd\_%' ESCAPE '\'),
    CHECK (primary_provider_org != secondary_provider_org)
);

CREATE INDEX idx_uniswap_v2_pair_event_v2_log_candidate_plan
    ON uniswap_v2_pair_event_v2_log_candidate (plan_id);

CREATE INDEX idx_uniswap_v2_pair_event_v2_log_candidate_auth_gen
    ON uniswap_v2_pair_event_v2_log_candidate (plan_id, session_auth_generation);

-- ---------------------------------------------------------------------------
-- Required blocks for a candidate (expected hash nullable only for boundary-only)
-- ---------------------------------------------------------------------------
CREATE TABLE uniswap_v2_pair_event_v2_log_candidate_block (
    plan_id TEXT NOT NULL,
    domain_id TEXT NOT NULL,
    block_number INTEGER NOT NULL CHECK (block_number >= 0),
    expected_block_hash TEXT
        CHECK (
            expected_block_hash IS NULL
            OR (
                length(expected_block_hash) = 66
                AND lower(expected_block_hash) = expected_block_hash
                AND expected_block_hash LIKE '0x%'
            )
        ),
    is_boundary INTEGER NOT NULL CHECK (is_boundary IN (0, 1)),
    PRIMARY KEY (plan_id, domain_id, block_number),
    FOREIGN KEY (plan_id, domain_id)
        REFERENCES uniswap_v2_pair_event_v2_log_candidate (plan_id, domain_id)
        ON DELETE CASCADE ON UPDATE RESTRICT,
    CHECK (plan_id LIKE 'plan\_%' ESCAPE '\'),
    CHECK (domain_id LIKE 'qd\_%' ESCAPE '\'),
    -- Boundary-only blocks may omit expected hash; event blocks must carry one.
    CHECK (
        (is_boundary = 1)
        OR (is_boundary = 0 AND expected_block_hash IS NOT NULL)
    )
);

CREATE INDEX idx_uniswap_v2_pair_event_v2_candidate_block_number
    ON uniswap_v2_pair_event_v2_log_candidate_block (plan_id, block_number);

CREATE INDEX idx_uniswap_v2_pair_event_v2_candidate_block_pending
    ON uniswap_v2_pair_event_v2_log_candidate_block (block_number);

-- ---------------------------------------------------------------------------
-- Covering indexes for production claim order and header work
-- (plan_id, status, domain_id) supports ORDER BY domain_id without temp sort
-- when filtered by plan_id + PENDING.
-- ---------------------------------------------------------------------------
CREATE INDEX idx_uniswap_v2_pair_event_v2_query_node_claim_domain
    ON uniswap_v2_pair_event_v2_query_node (plan_id, status, domain_id);

-- Header (plan_id, block_number) uniqueness/index already exists from 0018/0019
-- as UNIQUE INDEX idx_uniswap_v2_pair_event_v2_header_plan_block — do not recreate.

-- ---------------------------------------------------------------------------
-- Shared multi-process resume generation (O(plans)). Bumping invalidates
-- candidate.session_auth_generation marks so every process re-replays before
-- exclusion. Candidates committed under a live generation appear as unauth
-- (NULL or stale) and are selected by bounded unauth pages — no watermark race.
-- ---------------------------------------------------------------------------
CREATE TABLE uniswap_v2_pair_event_v2_plan_resume_session (
    plan_id TEXT PRIMARY KEY,
    active_generation INTEGER NOT NULL
        CHECK (active_generation >= 1),
    updated_at TEXT NOT NULL,
    FOREIGN KEY (plan_id) REFERENCES uniswap_v2_pair_event_v2_plan (plan_id)
        ON DELETE CASCADE ON UPDATE RESTRICT,
    CHECK (plan_id LIKE 'plan\_%' ESCAPE '\')
);

-- ---------------------------------------------------------------------------
-- Exact header backlog: transactionally coherent, multi-process durable.
-- Rows are distinct candidate-required blocks lacking a canonical header.
-- Metric row is O(1) exact count updated with INSERT/DELETE of backlog rows.
-- ---------------------------------------------------------------------------
CREATE TABLE uniswap_v2_pair_event_v2_header_backlog (
    plan_id TEXT NOT NULL,
    block_number INTEGER NOT NULL CHECK (block_number >= 0),
    PRIMARY KEY (plan_id, block_number),
    FOREIGN KEY (plan_id) REFERENCES uniswap_v2_pair_event_v2_plan (plan_id)
        ON DELETE CASCADE ON UPDATE RESTRICT,
    CHECK (plan_id LIKE 'plan\_%' ESCAPE '\')
);

CREATE INDEX idx_uniswap_v2_pair_event_v2_header_backlog_plan
    ON uniswap_v2_pair_event_v2_header_backlog (plan_id);

CREATE TABLE uniswap_v2_pair_event_v2_header_backlog_metric (
    plan_id TEXT PRIMARY KEY,
    missing_count INTEGER NOT NULL CHECK (missing_count >= 0),
    FOREIGN KEY (plan_id) REFERENCES uniswap_v2_pair_event_v2_plan (plan_id)
        ON DELETE CASCADE ON UPDATE RESTRICT,
    CHECK (plan_id LIKE 'plan\_%' ESCAPE '\')
);
