-- DATA-012 / REVIEW-0231: record the eth_chainId acquisition in receipt lineage.
--
-- Forward-only. Migrations 0009-0012 are complete and are not edited.
--
-- The chain identity check is a production acquisition, not a preflight: it reads
-- from the same endpoint, its response is preserved, and every event this receipt
-- publishes is only trustworthy if that response said mainnet. Recording it here
-- lets replay re-verify the chain identity offline from preserved bytes instead of
-- trusting that some earlier online run checked it.
--
-- The lineage is written on every chunk receipt rather than only the first, so each
-- chunk independently carries proof of the chain it was acquired from. A receipt
-- written before this migration keeps the '' default and is refused at replay,
-- because it cannot prove which chain produced it.

ALTER TABLE uniswap_v2_pair_created_chunk_receipt_v3
    ADD COLUMN chain_id_request_json TEXT NOT NULL DEFAULT '';

ALTER TABLE uniswap_v2_pair_created_chunk_receipt_v3
    ADD COLUMN chain_id_raw_object_id TEXT NOT NULL DEFAULT '';

ALTER TABLE uniswap_v2_pair_created_chunk_receipt_v3
    ADD COLUMN chain_id_acquisition_id TEXT NOT NULL DEFAULT '';

ALTER TABLE uniswap_v2_pair_created_chunk_receipt_v3
    ADD COLUMN chain_id_acquired_at TEXT NOT NULL DEFAULT '';
