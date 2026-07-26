CREATE TABLE IF NOT EXISTS uniswap_v2_pair_created_chunk_receipt_v2 (
    chain TEXT NOT NULL,
    factory TEXT NOT NULL,
    topic TEXT NOT NULL,
    start_block INTEGER NOT NULL,
    end_block INTEGER NOT NULL,
    end_block_hash TEXT NOT NULL,
    logs_raw_object_id TEXT NOT NULL,
    header_raw_object_ids_json TEXT NOT NULL,
    completed_at TEXT NOT NULL,
    PRIMARY KEY (chain, factory, topic, start_block, end_block)
);
