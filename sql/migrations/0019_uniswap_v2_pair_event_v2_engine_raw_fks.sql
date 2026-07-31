-- DEX-003 / ADR-0015 §9: v2 engine persistence — composite acquisition/raw FKs.
--
-- Forward-only. Rebuilds three tables to add the composite acquisition↔raw
-- foreign keys required by ADR-0015 §9.2 (exact composite acquisition/raw pairing):
--
--   1. uniswap_v2_pair_event_v2_engine_event (declared in 0018)
--   2. uniswap_v2_pair_event_v2_canonical_header_receipt (declared in 0017)
--   3. uniswap_v2_pair_event_v2_leaf_receipt (declared in 0017)
--
-- SQLite cannot ALTER TABLE to add foreign keys, so each table is rebuilt:
-- the legacy table is renamed aside (keeping every row), the new table is
-- created with the additional composite FKs, and the rows are copied over.
-- Copying any legacy row that violates the new pairing FKs fails atomically:
-- the runner executes this whole migration in one transaction, so nothing is
-- changed and the migration is not entered in migration history.
--
-- The leaf-header dependency table is rebuilt around the parent swaps so its
-- same-plan composite ownership keeps referencing the recreated parents.
--
-- Renaming a parent table rewrites child FK references to the new name, so
-- the detached dependency rows stay valid while the parents are rebuilt and
-- are copied last, once the new parents hold the migrated rows.

-- 1. Detach the dependent table first (child of leaf_receipt and header_receipt).
ALTER TABLE uniswap_v2_pair_event_v2_leaf_header_dependency
    RENAME TO zz_legacy_leaf_header_dependency;

-- 2. Detach the three parent tables being rebuilt (rows preserved).
ALTER TABLE uniswap_v2_pair_event_v2_engine_event
    RENAME TO zz_legacy_engine_event;
ALTER TABLE uniswap_v2_pair_event_v2_leaf_receipt
    RENAME TO zz_legacy_leaf_receipt;
ALTER TABLE uniswap_v2_pair_event_v2_canonical_header_receipt
    RENAME TO zz_legacy_canonical_header_receipt;

-- 3. Engine event: rebuild with composite acquisition↔raw FKs, copy rows.
CREATE TABLE uniswap_v2_pair_event_v2_engine_event (
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
    FOREIGN KEY (primary_acquisition_id, primary_raw_object_id)
        REFERENCES raw_acquisition(acquisition_id, raw_object_id)
        ON DELETE RESTRICT ON UPDATE RESTRICT,
    FOREIGN KEY (secondary_acquisition_id, secondary_raw_object_id)
        REFERENCES raw_acquisition(acquisition_id, raw_object_id)
        ON DELETE RESTRICT ON UPDATE RESTRICT,
    CHECK ((primary_raw_object_id IS NULL) = (primary_acquisition_id IS NULL)),
    CHECK ((secondary_raw_object_id IS NULL) = (secondary_acquisition_id IS NULL))
);

INSERT INTO uniswap_v2_pair_event_v2_engine_event
    SELECT * FROM zz_legacy_engine_event;

-- 4. Leaf receipt: rebuild with composite log acquisition↔raw FKs, copy rows.
CREATE TABLE uniswap_v2_pair_event_v2_leaf_receipt (
    leaf_receipt_id TEXT PRIMARY KEY
        CHECK (leaf_receipt_id LIKE 'leaf\_%' ESCAPE '\'),
    plan_id TEXT NOT NULL,
    domain_id TEXT NOT NULL,
    start_block INTEGER NOT NULL,
    end_block INTEGER NOT NULL,
    addresses_json TEXT NOT NULL,
    topics_json TEXT NOT NULL,
    primary_provider_org TEXT NOT NULL,
    secondary_provider_org TEXT NOT NULL,
    primary_logs_raw_object_id TEXT NOT NULL,
    secondary_logs_raw_object_id TEXT NOT NULL,
    primary_logs_acquisition_id TEXT NOT NULL,
    secondary_logs_acquisition_id TEXT NOT NULL,
    log_count INTEGER NOT NULL,
    log_identity_sha256 TEXT NOT NULL,
    canonical_header_receipt_ids_json TEXT NOT NULL,
    log_identity_version TEXT NOT NULL,
    receipt_schema_version TEXT NOT NULL,
    reconciliation_status TEXT NOT NULL,
    completed_at TEXT NOT NULL,
    UNIQUE (plan_id, leaf_receipt_id),
    FOREIGN KEY (plan_id) REFERENCES uniswap_v2_pair_event_v2_plan (plan_id)
        ON DELETE CASCADE ON UPDATE RESTRICT,
    FOREIGN KEY (plan_id, domain_id)
        REFERENCES uniswap_v2_pair_event_v2_query_node (plan_id, domain_id)
        ON DELETE RESTRICT ON UPDATE RESTRICT,
    FOREIGN KEY (primary_logs_acquisition_id, primary_logs_raw_object_id)
        REFERENCES raw_acquisition(acquisition_id, raw_object_id)
        ON DELETE RESTRICT ON UPDATE RESTRICT,
    FOREIGN KEY (secondary_logs_acquisition_id, secondary_logs_raw_object_id)
        REFERENCES raw_acquisition(acquisition_id, raw_object_id)
        ON DELETE RESTRICT ON UPDATE RESTRICT,
    CHECK (leaf_receipt_id LIKE 'leaf\_%' ESCAPE '\'),
    CHECK (plan_id LIKE 'plan\_%' ESCAPE '\'),
    CHECK (domain_id LIKE 'qd\_%' ESCAPE '\'),
    CHECK (end_block >= start_block),
    CHECK (log_count >= 0),
    CHECK (primary_provider_org != secondary_provider_org),
    CHECK (log_identity_version = '2'),
    CHECK (receipt_schema_version = '1'),
    CHECK (reconciliation_status = 'AGREED')
);

INSERT INTO uniswap_v2_pair_event_v2_leaf_receipt
    SELECT * FROM zz_legacy_leaf_receipt;

-- 5. Canonical header receipt: rebuild with composite acquisition↔raw FKs, copy rows.
CREATE TABLE uniswap_v2_pair_event_v2_canonical_header_receipt (
    header_receipt_id TEXT PRIMARY KEY
        CHECK (header_receipt_id LIKE 'chdr\_%' ESCAPE '\'),
    plan_id TEXT NOT NULL,
    block_number INTEGER NOT NULL,
    block_hash TEXT NOT NULL,
    block_timestamp INTEGER NOT NULL,
    primary_provider_org TEXT NOT NULL,
    secondary_provider_org TEXT NOT NULL,
    primary_raw_object_id TEXT NOT NULL,
    secondary_raw_object_id TEXT NOT NULL,
    primary_acquisition_id TEXT NOT NULL,
    secondary_acquisition_id TEXT NOT NULL,
    receipt_schema_version TEXT NOT NULL,
    completed_at TEXT NOT NULL,
    UNIQUE (plan_id, header_receipt_id),
    FOREIGN KEY (plan_id) REFERENCES uniswap_v2_pair_event_v2_plan (plan_id)
        ON DELETE CASCADE ON UPDATE RESTRICT,
    FOREIGN KEY (primary_acquisition_id, primary_raw_object_id)
        REFERENCES raw_acquisition(acquisition_id, raw_object_id)
        ON DELETE RESTRICT ON UPDATE RESTRICT,
    FOREIGN KEY (secondary_acquisition_id, secondary_raw_object_id)
        REFERENCES raw_acquisition(acquisition_id, raw_object_id)
        ON DELETE RESTRICT ON UPDATE RESTRICT,
    CHECK (header_receipt_id LIKE 'chdr\_%' ESCAPE '\'),
    CHECK (plan_id LIKE 'plan\_%' ESCAPE '\'),
    CHECK (block_number >= 0),
    CHECK (primary_provider_org != secondary_provider_org),
    CHECK (receipt_schema_version = '1')
);

INSERT INTO uniswap_v2_pair_event_v2_canonical_header_receipt
    SELECT * FROM zz_legacy_canonical_header_receipt;

-- 6. Rebuild the dependency table around the parent swaps and copy rows.
--    The copied rows are validated against the rebuilt parents.
CREATE TABLE uniswap_v2_pair_event_v2_leaf_header_dependency (
    plan_id TEXT NOT NULL,
    leaf_receipt_id TEXT NOT NULL,
    header_receipt_id TEXT NOT NULL,
    PRIMARY KEY (plan_id, leaf_receipt_id, header_receipt_id),
    FOREIGN KEY (plan_id, leaf_receipt_id)
        REFERENCES uniswap_v2_pair_event_v2_leaf_receipt (plan_id, leaf_receipt_id)
        ON DELETE CASCADE ON UPDATE RESTRICT,
    FOREIGN KEY (plan_id, header_receipt_id)
        REFERENCES uniswap_v2_pair_event_v2_canonical_header_receipt (plan_id, header_receipt_id)
        ON DELETE RESTRICT ON UPDATE RESTRICT
);

INSERT INTO uniswap_v2_pair_event_v2_leaf_header_dependency
    SELECT * FROM zz_legacy_leaf_header_dependency;

-- 7. Drop the detached legacy tables (child first). Any legacy row that
--    violates the new pairing FKs failed its copy above and aborted this
--    migration atomically, so only valid rows reach this point.
DROP TABLE zz_legacy_leaf_header_dependency;
DROP TABLE zz_legacy_leaf_receipt;
DROP TABLE zz_legacy_canonical_header_receipt;
DROP TABLE zz_legacy_engine_event;

-- 8. Recreate the original indexes on the rebuilt tables.
CREATE INDEX IF NOT EXISTS idx_uniswap_v2_pair_event_v2_engine_event_plan
    ON uniswap_v2_pair_event_v2_engine_event (plan_id, created_at);

CREATE INDEX IF NOT EXISTS idx_uniswap_v2_pair_event_v2_header_block
    ON uniswap_v2_pair_event_v2_canonical_header_receipt (plan_id, block_number);

CREATE UNIQUE INDEX IF NOT EXISTS idx_uniswap_v2_pair_event_v2_header_plan_block
    ON uniswap_v2_pair_event_v2_canonical_header_receipt (plan_id, block_number);

CREATE UNIQUE INDEX IF NOT EXISTS idx_uniswap_v2_pair_event_v2_header_plan_receipt
    ON uniswap_v2_pair_event_v2_canonical_header_receipt (plan_id, header_receipt_id);

CREATE INDEX IF NOT EXISTS idx_uniswap_v2_pair_event_v2_leaf_domain
    ON uniswap_v2_pair_event_v2_leaf_receipt (plan_id, domain_id);

CREATE UNIQUE INDEX IF NOT EXISTS idx_uniswap_v2_pair_event_v2_leaf_plan_domain
    ON uniswap_v2_pair_event_v2_leaf_receipt (plan_id, domain_id);

CREATE UNIQUE INDEX IF NOT EXISTS idx_uniswap_v2_pair_event_v2_leaf_plan_receipt
    ON uniswap_v2_pair_event_v2_leaf_receipt (plan_id, leaf_receipt_id);

CREATE INDEX IF NOT EXISTS idx_uniswap_v2_pair_event_v2_dependency_header
    ON uniswap_v2_pair_event_v2_leaf_header_dependency (plan_id, header_receipt_id);

CREATE UNIQUE INDEX IF NOT EXISTS idx_uniswap_v2_pair_event_v2_dep_plan_pair
    ON uniswap_v2_pair_event_v2_leaf_header_dependency (plan_id, leaf_receipt_id, header_receipt_id);
