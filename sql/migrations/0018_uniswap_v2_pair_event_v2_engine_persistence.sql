-- DEX-003 / ADR-0015 §9: v2 bounded acquisition engine persistence contracts.
--
-- Forward-only. Implements every exact contract declared at the top of
-- uniswap_v2_pair_events_v2_engine.py: chain identity, engine event, execution
-- policy, terminal receipt, the raw_acquisition composite pairing key, and the
-- header/leaf/dependency uniqueness contracts that resolve canonical winners.
--
-- SQLite does not support ALTER TABLE ... ADD CONSTRAINT; unique constraints
-- on existing tables are installed via CREATE UNIQUE INDEX, and new tables are
-- created inline with all foreign keys.

-- 1. Parent composite pairing key for all acquisition↔raw FK enforcement.
CREATE UNIQUE INDEX IF NOT EXISTS idx_raw_acquisition_pair
    ON raw_acquisition(acquisition_id, raw_object_id);

-- 2. Chain identity: one durable dual-provider mainnet authentication per plan.
CREATE TABLE IF NOT EXISTS uniswap_v2_pair_event_v2_chain_identity_receipt (
    chain_identity_receipt_id TEXT PRIMARY KEY
        CHECK (chain_identity_receipt_id LIKE 'chain\_%' ESCAPE '\'),
    plan_id TEXT NOT NULL UNIQUE,
    chain_id INTEGER NOT NULL CHECK (chain_id = 1),
    primary_provider_org TEXT NOT NULL,
    secondary_provider_org TEXT NOT NULL CHECK (primary_provider_org != secondary_provider_org),
    primary_raw_object_id TEXT NOT NULL CHECK (primary_raw_object_id LIKE 'raw\_%' ESCAPE '\'),
    secondary_raw_object_id TEXT NOT NULL CHECK (secondary_raw_object_id LIKE 'raw\_%' ESCAPE '\'),
    primary_acquisition_id TEXT NOT NULL CHECK (primary_acquisition_id LIKE 'acq\_%' ESCAPE '\'),
    secondary_acquisition_id TEXT NOT NULL CHECK (secondary_acquisition_id LIKE 'acq\_%' ESCAPE '\'),
    schema_version TEXT NOT NULL CHECK (schema_version = '1'),
    completed_at TEXT NOT NULL,
    FOREIGN KEY (plan_id) REFERENCES uniswap_v2_pair_event_v2_plan (plan_id)
        ON DELETE CASCADE ON UPDATE RESTRICT,
    FOREIGN KEY (primary_acquisition_id, primary_raw_object_id)
        REFERENCES raw_acquisition(acquisition_id, raw_object_id)
        ON DELETE RESTRICT ON UPDATE RESTRICT,
    FOREIGN KEY (secondary_acquisition_id, secondary_raw_object_id)
        REFERENCES raw_acquisition(acquisition_id, raw_object_id)
        ON DELETE RESTRICT ON UPDATE RESTRICT
);

-- 3. Execution policy: immutable authority-affecting settings per plan.
CREATE TABLE IF NOT EXISTS uniswap_v2_pair_event_v2_execution_policy (
    policy_id TEXT PRIMARY KEY
        CHECK (policy_id LIKE 'pol\_%' ESCAPE '\'),
    plan_id TEXT NOT NULL UNIQUE,
    identity_payload_json TEXT NOT NULL,
    schema_version TEXT NOT NULL CHECK (schema_version = '1'),
    created_at TEXT NOT NULL,
    FOREIGN KEY (plan_id) REFERENCES uniswap_v2_pair_event_v2_plan (plan_id)
        ON DELETE CASCADE ON UPDATE RESTRICT
);

-- 4. Engine event: durable audit journal of every decision/failure/retry.
CREATE TABLE IF NOT EXISTS uniswap_v2_pair_event_v2_engine_event (
    event_id TEXT PRIMARY KEY
        CHECK (event_id LIKE 'evt\_%' ESCAPE '\'),
    schema_version TEXT NOT NULL CHECK (schema_version = '1'),
    plan_id TEXT NOT NULL,
    domain_id TEXT CHECK (domain_id LIKE 'qd\_%' ESCAPE '\'),
    attempt INTEGER NOT NULL CHECK (attempt >= 0),
    event_kind TEXT NOT NULL
        CHECK (event_kind IN (
            'failure', 'lease_expiry', 'provider_disagreement',
            'retry_decision', 'split_decision', 'terminal_blocker'
        )),
    failure_class TEXT
        CHECK (failure_class IN (
            'http_429', 'explicit_range_limit', 'body_size_pressure',
            'result_size_pressure', 'provider_disagreement', 'transport',
            'authentication', 'http_status', 'malformed_json', 'rpc_error',
            'boundary_mismatch', 'header_conflict', 'persistence', 'internal'
        )),
    decision TEXT,
    provider_org TEXT,
    request_json TEXT,
    primary_raw_object_id TEXT,
    secondary_raw_object_id TEXT,
    primary_acquisition_id TEXT,
    secondary_acquisition_id TEXT,
    detail_json TEXT NOT NULL,
    created_at TEXT NOT NULL,
    FOREIGN KEY (plan_id) REFERENCES uniswap_v2_pair_event_v2_plan (plan_id)
        ON DELETE CASCADE ON UPDATE RESTRICT,
    FOREIGN KEY (plan_id, domain_id)
        REFERENCES uniswap_v2_pair_event_v2_query_node (plan_id, domain_id)
        ON DELETE RESTRICT ON UPDATE RESTRICT,
    CHECK ((primary_raw_object_id IS NULL) = (primary_acquisition_id IS NULL)),
    CHECK ((secondary_raw_object_id IS NULL) = (secondary_acquisition_id IS NULL))
);

CREATE INDEX IF NOT EXISTS idx_uniswap_v2_pair_event_v2_engine_event_plan
    ON uniswap_v2_pair_event_v2_engine_event (plan_id, created_at);

-- 5. Terminal receipt: durable claim-bound terminal winner identity (one per node).
CREATE TABLE IF NOT EXISTS uniswap_v2_pair_event_v2_terminal_receipt (
    terminal_receipt_id TEXT PRIMARY KEY
        CHECK (terminal_receipt_id LIKE 'term\_%' ESCAPE '\'),
    plan_id TEXT NOT NULL,
    domain_id TEXT NOT NULL,
    terminal_mode TEXT NOT NULL
        CHECK (terminal_mode IN (
            'lease_expired', 'unsplittable_singleton', 'http_429',
            'explicit_range_limit', 'body_size_pressure', 'result_size_pressure',
            'provider_disagreement', 'transport', 'authentication', 'http_status',
            'malformed_json', 'rpc_error', 'boundary_mismatch', 'header_conflict',
            'persistence', 'internal'
        )),
    attempt INTEGER NOT NULL CHECK (attempt >= 0),
    schema_version TEXT NOT NULL CHECK (schema_version = '1'),
    completed_at TEXT NOT NULL,
    UNIQUE (plan_id, domain_id),
    FOREIGN KEY (plan_id, domain_id)
        REFERENCES uniswap_v2_pair_event_v2_query_node (plan_id, domain_id)
        ON DELETE RESTRICT ON UPDATE RESTRICT
);

-- 6. Header uniqueness/ownership contracts (complements 0017).
CREATE UNIQUE INDEX IF NOT EXISTS idx_uniswap_v2_pair_event_v2_header_plan_block
    ON uniswap_v2_pair_event_v2_canonical_header_receipt (plan_id, block_number);
CREATE UNIQUE INDEX IF NOT EXISTS idx_uniswap_v2_pair_event_v2_header_plan_receipt
    ON uniswap_v2_pair_event_v2_canonical_header_receipt (plan_id, header_receipt_id);

-- 7. Leaf uniqueness/ownership contracts (complements 0017).
CREATE UNIQUE INDEX IF NOT EXISTS idx_uniswap_v2_pair_event_v2_leaf_plan_domain
    ON uniswap_v2_pair_event_v2_leaf_receipt (plan_id, domain_id);
CREATE UNIQUE INDEX IF NOT EXISTS idx_uniswap_v2_pair_event_v2_leaf_plan_receipt
    ON uniswap_v2_pair_event_v2_leaf_receipt (plan_id, leaf_receipt_id);

-- 8. Dependency ownership: same-plan leaf→header binding (complements 0017).
CREATE UNIQUE INDEX IF NOT EXISTS idx_uniswap_v2_pair_event_v2_dep_plan_pair
    ON uniswap_v2_pair_event_v2_leaf_header_dependency (plan_id, leaf_receipt_id, header_receipt_id);
