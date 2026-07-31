-- DEX-003: retain secondary event-block header lineage on pair-event receipts.
--
-- Forward-only. Migration 0014 records dual eth_getLogs and dual end-block headers,
-- but only primary event-block headers were stored for offline decode. Secondary
-- event-block headers were compared live and discarded, so offline replay could not
-- re-prove dual timestamp/hash authority. This column carries the secondary
-- HeaderDependency list (same shape as header_dependencies_json).

ALTER TABLE uniswap_v2_pair_event_chunk_receipt
    ADD COLUMN secondary_header_dependencies_json TEXT NOT NULL DEFAULT '[]';
