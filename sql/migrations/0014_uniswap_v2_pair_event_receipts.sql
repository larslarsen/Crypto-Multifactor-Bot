-- DEX-003 / ADR-0015: Swap and Sync pair-event chunk receipts with dual-RPC authority.
--
-- Forward-only. Migrations 0009-0013 cover factory PairCreated only and are not edited.
--
-- Swap and Sync have no global factory ordinal. Completeness therefore requires either
-- count-and-identity agreement from two independent RPC providers per block chunk, or
-- receipt-level reconstruction from canonical blocks. This table records the dual-RPC
-- path: every completed chunk stores both providers' eth_getLogs acquisitions, the
-- agreed log-identity digest, dual end-block header lineage, and the event-block
-- headers needed for offline replay. A single successful eth_getLogs is never enough
-- to write a receipt.
--
-- Disagreements and transport failures are retained as durable evidence so an
-- unresolved range is explainable and cannot be silently skipped.

CREATE TABLE IF NOT EXISTS uniswap_v2_pair_event_chunk_receipt (
    chain TEXT NOT NULL,
    chain_id TEXT NOT NULL,
    pair TEXT NOT NULL,
    topic TEXT NOT NULL,
    start_block INTEGER NOT NULL,
    end_block INTEGER NOT NULL,
    primary_provider_id TEXT NOT NULL,
    primary_logs_request_json TEXT NOT NULL,
    primary_logs_raw_object_id TEXT NOT NULL,
    primary_logs_acquisition_id TEXT NOT NULL,
    primary_logs_acquired_at TEXT NOT NULL,
    secondary_provider_id TEXT NOT NULL,
    secondary_logs_request_json TEXT NOT NULL,
    secondary_logs_raw_object_id TEXT NOT NULL,
    secondary_logs_acquisition_id TEXT NOT NULL,
    secondary_logs_acquired_at TEXT NOT NULL,
    log_count INTEGER NOT NULL,
    log_identity_sha256 TEXT NOT NULL,
    reconciliation_status TEXT NOT NULL,
    end_block_number INTEGER NOT NULL,
    end_block_hash TEXT NOT NULL,
    primary_end_header_request_json TEXT NOT NULL,
    primary_end_header_raw_object_id TEXT NOT NULL,
    primary_end_header_acquisition_id TEXT NOT NULL,
    primary_end_header_acquired_at TEXT NOT NULL,
    secondary_end_block_hash TEXT NOT NULL,
    secondary_end_header_request_json TEXT NOT NULL,
    secondary_end_header_raw_object_id TEXT NOT NULL,
    secondary_end_header_acquisition_id TEXT NOT NULL,
    secondary_end_header_acquired_at TEXT NOT NULL,
    header_dependencies_json TEXT NOT NULL,
    completed_at TEXT NOT NULL,
    chain_id_request_json TEXT NOT NULL,
    chain_id_raw_object_id TEXT NOT NULL,
    chain_id_acquisition_id TEXT NOT NULL,
    chain_id_acquired_at TEXT NOT NULL,
    PRIMARY KEY (chain, pair, topic, start_block, end_block),
    CHECK (end_block >= start_block),
    CHECK (start_block >= 10000835),
    CHECK (end_block_number = end_block),
    CHECK (chain_id = '0x1'),
    CHECK (log_count >= 0),
    CHECK (reconciliation_status = 'AGREED'),
    CHECK (primary_provider_id != secondary_provider_id),
    CHECK (end_block_hash = secondary_end_block_hash)
);

CREATE INDEX IF NOT EXISTS idx_uniswap_v2_pair_event_receipt_coverage
    ON uniswap_v2_pair_event_chunk_receipt (
        chain, pair, topic, start_block, end_block
    );

CREATE TABLE IF NOT EXISTS uniswap_v2_pair_event_transport_failure (
    failure_id INTEGER PRIMARY KEY AUTOINCREMENT,
    chain TEXT NOT NULL,
    pair TEXT NOT NULL,
    topic TEXT NOT NULL,
    provider_id TEXT NOT NULL,
    method TEXT NOT NULL,
    request_json TEXT NOT NULL,
    start_block INTEGER NOT NULL,
    end_block INTEGER NOT NULL,
    failure_kind TEXT NOT NULL,
    status_code INTEGER,
    raw_object_id TEXT,
    acquisition_id TEXT,
    detail TEXT NOT NULL,
    occurred_at TEXT NOT NULL,
    CHECK (failure_kind IN ('transport', 'http_status', 'invalid_json', 'rpc_error'))
);

CREATE INDEX IF NOT EXISTS idx_uniswap_v2_pair_event_transport_failure_range
    ON uniswap_v2_pair_event_transport_failure (
        chain, pair, topic, start_block, end_block
    );

-- Provider disagreement is not a transport failure: both providers answered, but their
-- log identities, block hashes, or end-block headers do not match. The chunk remains
-- unresolved until a later acquisition reconciles or the operator intervenes.
CREATE TABLE IF NOT EXISTS uniswap_v2_pair_event_provider_disagreement (
    disagreement_id INTEGER PRIMARY KEY AUTOINCREMENT,
    chain TEXT NOT NULL,
    pair TEXT NOT NULL,
    topic TEXT NOT NULL,
    start_block INTEGER NOT NULL,
    end_block INTEGER NOT NULL,
    primary_provider_id TEXT NOT NULL,
    secondary_provider_id TEXT NOT NULL,
    primary_logs_raw_object_id TEXT,
    secondary_logs_raw_object_id TEXT,
    primary_end_block_hash TEXT,
    secondary_end_block_hash TEXT,
    primary_log_count INTEGER,
    secondary_log_count INTEGER,
    primary_identity_sha256 TEXT,
    secondary_identity_sha256 TEXT,
    detail TEXT NOT NULL,
    occurred_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_uniswap_v2_pair_event_disagreement_range
    ON uniswap_v2_pair_event_provider_disagreement (
        chain, pair, topic, start_block, end_block
    );
