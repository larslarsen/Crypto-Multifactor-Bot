ALTER TABLE uniswap_v2_pair_created_chunk_receipt ADD COLUMN chain TEXT NOT NULL DEFAULT 'ethereum';
ALTER TABLE uniswap_v2_pair_created_chunk_receipt ADD COLUMN factory TEXT NOT NULL DEFAULT '';
ALTER TABLE uniswap_v2_pair_created_chunk_receipt ADD COLUMN topic TEXT NOT NULL DEFAULT '';
ALTER TABLE uniswap_v2_pair_created_chunk_receipt ADD COLUMN header_raw_object_ids_json TEXT NOT NULL DEFAULT '[]';
