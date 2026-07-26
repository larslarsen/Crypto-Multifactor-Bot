CREATE TABLE IF NOT EXISTS uniswap_v2_pair_created_chunk_receipt (
    start_block INTEGER NOT NULL,
    end_block INTEGER NOT NULL,
    end_block_hash TEXT NOT NULL,
    logs_raw_object_id TEXT NOT NULL,
    completed_at TEXT NOT NULL,
    PRIMARY KEY (start_block, end_block)
);
