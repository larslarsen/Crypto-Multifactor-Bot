-- DATA-012: bind PairCreated chunk receipts to acquisition identity.
--
-- Forward-only. Migrations 0009, 0010 and 0011 are complete and are not edited.
-- The v2 receipt table proved insufficient: it recorded which raw objects a chunk
-- depended on, but not which acquisition produced them, nor the exact JSON-RPC
-- request they answer, nor the per-response acquisition timestamps. Replay could
-- therefore not prove that the preserved bytes answer the request the caller is
-- asking to replay. v3 binds every dependency to (request, raw object,
-- acquisition id, acquired_at) so replay is request-bound and fully offline.
--
-- Header dependencies are stored as a JSON array of objects, each carrying
-- block_number, block_hash, request_json, raw_object_id, acquisition_id and
-- acquired_at, so an event block header can be authenticated without the network.

CREATE TABLE IF NOT EXISTS uniswap_v2_pair_created_chunk_receipt_v3 (
    chain TEXT NOT NULL,
    chain_id TEXT NOT NULL,
    factory TEXT NOT NULL,
    topic TEXT NOT NULL,
    start_block INTEGER NOT NULL,
    end_block INTEGER NOT NULL,
    logs_request_json TEXT NOT NULL,
    logs_raw_object_id TEXT NOT NULL,
    logs_acquisition_id TEXT NOT NULL,
    logs_acquired_at TEXT NOT NULL,
    end_block_number INTEGER NOT NULL,
    end_block_hash TEXT NOT NULL,
    end_header_request_json TEXT NOT NULL,
    end_header_raw_object_id TEXT NOT NULL,
    end_header_acquisition_id TEXT NOT NULL,
    end_header_acquired_at TEXT NOT NULL,
    header_dependencies_json TEXT NOT NULL,
    completed_at TEXT NOT NULL,
    PRIMARY KEY (chain, factory, topic, start_block, end_block),
    CHECK (end_block >= start_block),
    CHECK (start_block >= 0),
    CHECK (end_block_number = end_block),
    CHECK (chain_id = '0x1')
);

-- Range scans during resume and replay are keyed by ingestion identity first.
CREATE INDEX IF NOT EXISTS idx_uniswap_v2_receipt_v3_coverage
    ON uniswap_v2_pair_created_chunk_receipt_v3 (chain, factory, topic, start_block, end_block);

-- Transport and protocol failures are evidence, not noise: a chunk that failed to
-- acquire must leave a durable record even when no bytes were received. raw_object_id
-- is NULL only for failures where the transport produced no response body at all.
CREATE TABLE IF NOT EXISTS uniswap_v2_pair_created_transport_failure (
    failure_id INTEGER PRIMARY KEY AUTOINCREMENT,
    chain TEXT NOT NULL,
    factory TEXT NOT NULL,
    topic TEXT NOT NULL,
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

CREATE INDEX IF NOT EXISTS idx_uniswap_v2_transport_failure_range
    ON uniswap_v2_pair_created_transport_failure (chain, factory, topic, start_block, end_block);
