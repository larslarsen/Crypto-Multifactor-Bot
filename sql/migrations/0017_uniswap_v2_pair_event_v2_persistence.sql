-- DEX-003 / ADR-0015 §9: block-major v2 persistence tables.
--
-- Forward-only. This replaces the empty partial v2 schema created by the
-- failed initial 0017 application. SQLite requires foreign keys in CREATE
-- TABLE, so every ownership relationship is declared inline.

CREATE TABLE uniswap_v2_pair_event_v2_plan (
    plan_id TEXT PRIMARY KEY,
    registry_dataset_id TEXT NOT NULL,
    identity_payload_json TEXT NOT NULL,
    event_provider_orgs_json TEXT NOT NULL,
    metadata_provider_orgs_json TEXT NOT NULL,
    root_block_size INTEGER NOT NULL,
    initial_cohort_size INTEGER NOT NULL,
    deployment_block INTEGER NOT NULL,
    cutoff_block INTEGER NOT NULL,
    plan_schema_version TEXT NOT NULL,
    created_at TEXT NOT NULL,
    CHECK (plan_id LIKE 'plan\_%' ESCAPE '\'),
    CHECK (registry_dataset_id = 'ds_42ce2515e226258557a06a374498547393bbc984db791c56fa19d81d7ef16d15'),
    CHECK (root_block_size = 5000),
    CHECK (initial_cohort_size IN (1, 8, 32, 64, 128)),
    CHECK (deployment_block = 10000835),
    CHECK (cutoff_block = 25600000),
    CHECK (plan_schema_version = '1')
);

CREATE INDEX idx_uniswap_v2_pair_event_v2_plan_registry
    ON uniswap_v2_pair_event_v2_plan (registry_dataset_id);

CREATE TABLE uniswap_v2_pair_event_v2_query_node (
    plan_id TEXT NOT NULL,
    domain_id TEXT NOT NULL,
    start_block INTEGER NOT NULL,
    end_block INTEGER NOT NULL,
    addresses_json TEXT NOT NULL,
    topics_json TEXT NOT NULL,
    status TEXT NOT NULL,
    parent_domain_id TEXT,
    split_reason TEXT,
    attempt INTEGER NOT NULL,
    updated_at TEXT NOT NULL,
    PRIMARY KEY (plan_id, domain_id),
    FOREIGN KEY (plan_id) REFERENCES uniswap_v2_pair_event_v2_plan (plan_id)
        ON DELETE CASCADE ON UPDATE RESTRICT,
    FOREIGN KEY (plan_id, parent_domain_id)
        REFERENCES uniswap_v2_pair_event_v2_query_node (plan_id, domain_id)
        ON DELETE RESTRICT ON UPDATE RESTRICT,
    CHECK (plan_id LIKE 'plan\_%' ESCAPE '\'),
    CHECK (domain_id LIKE 'qd\_%' ESCAPE '\'),
    CHECK (end_block >= start_block),
    CHECK (status IN ('PENDING', 'IN_FLIGHT', 'AGREED', 'SPLIT')),
    CHECK (
        split_reason IS NULL
        OR split_reason IN (
            'block_range_limit',
            'oversized_result',
            'provider_disagreement',
            'conservative_cap',
            'manual'
        )
    ),
    CHECK (attempt >= 0)
);

CREATE INDEX idx_uniswap_v2_pair_event_v2_query_node_status
    ON uniswap_v2_pair_event_v2_query_node (plan_id, status);

CREATE TABLE uniswap_v2_pair_event_v2_canonical_header_receipt (
    header_receipt_id TEXT PRIMARY KEY,
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
    CHECK (header_receipt_id LIKE 'chdr\_%' ESCAPE '\'),
    CHECK (plan_id LIKE 'plan\_%' ESCAPE '\'),
    CHECK (block_number >= 0),
    CHECK (primary_provider_org != secondary_provider_org),
    CHECK (receipt_schema_version = '1')
);

CREATE INDEX idx_uniswap_v2_pair_event_v2_header_block
    ON uniswap_v2_pair_event_v2_canonical_header_receipt (plan_id, block_number);

CREATE TABLE uniswap_v2_pair_event_v2_leaf_receipt (
    leaf_receipt_id TEXT PRIMARY KEY,
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

CREATE INDEX idx_uniswap_v2_pair_event_v2_leaf_domain
    ON uniswap_v2_pair_event_v2_leaf_receipt (plan_id, domain_id);

-- A leaf can depend on multiple shared headers. This normalized relation keeps
-- the FK graph auditable while the leaf's JSON list remains identity-bound.
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

CREATE INDEX idx_uniswap_v2_pair_event_v2_dependency_header
    ON uniswap_v2_pair_event_v2_leaf_header_dependency (plan_id, header_receipt_id);

CREATE TABLE uniswap_v2_pair_event_v2_query_lease (
    plan_id TEXT NOT NULL,
    domain_id TEXT NOT NULL,
    worker_id TEXT NOT NULL,
    lease_token TEXT NOT NULL,
    leased_at TEXT NOT NULL,
    expires_at TEXT NOT NULL,
    PRIMARY KEY (plan_id, domain_id),
    FOREIGN KEY (plan_id) REFERENCES uniswap_v2_pair_event_v2_plan (plan_id)
        ON DELETE CASCADE ON UPDATE RESTRICT,
    FOREIGN KEY (plan_id, domain_id)
        REFERENCES uniswap_v2_pair_event_v2_query_node (plan_id, domain_id)
        ON DELETE CASCADE ON UPDATE RESTRICT,
    CHECK (plan_id LIKE 'plan\_%' ESCAPE '\'),
    CHECK (domain_id LIKE 'qd\_%' ESCAPE '\'),
    CHECK (lease_token != ''),
    CHECK (expires_at >= leased_at)
);

CREATE TABLE uniswap_v2_pair_event_v2_coverage_product (
    plan_id TEXT NOT NULL,
    pool_address TEXT NOT NULL,
    topic TEXT NOT NULL,
    expected_start INTEGER NOT NULL,
    expected_end INTEGER NOT NULL,
    expected_block_count INTEGER NOT NULL,
    covered_block_count INTEGER NOT NULL,
    first_covered_block INTEGER,
    last_covered_block INTEGER,
    leaf_count INTEGER NOT NULL,
    has_gap INTEGER NOT NULL,
    has_overlap INTEGER NOT NULL,
    supporting_receipts_root TEXT NOT NULL,
    coverage_hash TEXT NOT NULL,
    is_complete INTEGER NOT NULL,
    schema_version TEXT NOT NULL,
    PRIMARY KEY (plan_id, pool_address, topic),
    FOREIGN KEY (plan_id) REFERENCES uniswap_v2_pair_event_v2_plan (plan_id)
        ON DELETE CASCADE ON UPDATE RESTRICT,
    CHECK (plan_id LIKE 'plan\_%' ESCAPE '\'),
    CHECK (expected_end >= expected_start),
    CHECK (expected_block_count >= 0),
    CHECK (covered_block_count >= 0),
    CHECK (leaf_count >= 0),
    CHECK (has_gap IN (0, 1)),
    CHECK (has_overlap IN (0, 1)),
    CHECK (is_complete IN (0, 1)),
    CHECK (schema_version = '1')
);
