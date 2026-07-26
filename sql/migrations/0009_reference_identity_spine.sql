-- ARCH-003: explicit four-level identity attributes.
-- Additive columns keep the REF-001 tables backward compatible.

ALTER TABLE ref_instrument ADD COLUMN identity_kind TEXT;
ALTER TABLE ref_instrument ADD COLUMN chain TEXT;
ALTER TABLE ref_instrument ADD COLUMN address TEXT;
ALTER TABLE ref_instrument ADD COLUMN fee_tier TEXT;
ALTER TABLE ref_instrument ADD COLUMN base_instrument_id TEXT
    REFERENCES ref_instrument(instrument_id);
ALTER TABLE ref_instrument ADD COLUMN quote_instrument_id TEXT
    REFERENCES ref_instrument(instrument_id);

ALTER TABLE ref_listing_event ADD COLUMN venue_symbol TEXT;

CREATE UNIQUE INDEX IF NOT EXISTS idx_ref_instrument_contract_identity
    ON ref_instrument(identity_kind, chain, address)
    WHERE identity_kind = 'token_contract';

CREATE UNIQUE INDEX IF NOT EXISTS idx_ref_instrument_pool_identity
    ON ref_instrument(identity_kind, chain, address, fee_tier)
    WHERE identity_kind = 'dex_pool';

CREATE INDEX IF NOT EXISTS idx_ref_instrument_pool_contracts
    ON ref_instrument(base_instrument_id, quote_instrument_id)
    WHERE identity_kind = 'dex_pool';

CREATE INDEX IF NOT EXISTS idx_ref_listing_venue_symbol
    ON ref_listing_event(venue_id, venue_symbol, valid_from, known_from);
