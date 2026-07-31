-- DEX-003: durable dual-provider ERC-20 decimals() receipts for resume.
--
-- Forward-only. Successful token-decimal acquisitions must not live only in
-- process memory: each completed (token, block_number) stores both providers'
-- eth_call request identity, raw object ids, acquisition ids, and the agreed
-- decimals value so offline resume can re-authenticate preserved bytes without
-- re-contacting the network.

CREATE TABLE IF NOT EXISTS uniswap_v2_token_decimals_receipt (
    chain TEXT NOT NULL,
    chain_id TEXT NOT NULL,
    token TEXT NOT NULL,
    block_number INTEGER NOT NULL,
    decimals INTEGER NOT NULL,
    primary_provider_id TEXT NOT NULL,
    secondary_provider_id TEXT NOT NULL,
    primary_request_json TEXT NOT NULL,
    primary_raw_object_id TEXT NOT NULL,
    primary_acquisition_id TEXT NOT NULL,
    primary_acquired_at TEXT NOT NULL,
    secondary_request_json TEXT NOT NULL,
    secondary_raw_object_id TEXT NOT NULL,
    secondary_acquisition_id TEXT NOT NULL,
    secondary_acquired_at TEXT NOT NULL,
    completed_at TEXT NOT NULL,
    PRIMARY KEY (chain, token, block_number),
    CHECK (chain_id = '0x1'),
    CHECK (block_number >= 0),
    CHECK (decimals >= 0 AND decimals <= 255),
    CHECK (primary_provider_id != secondary_provider_id)
);

CREATE INDEX IF NOT EXISTS idx_uniswap_v2_token_decimals_receipt_token
    ON uniswap_v2_token_decimals_receipt (chain, token, block_number);
