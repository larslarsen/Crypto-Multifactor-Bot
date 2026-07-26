-- ARCH-003 / REVIEW-0219: stable reference identities are TEXT; canonical
-- integer keys are separate, explicit compatibility surrogates.

CREATE TABLE IF NOT EXISTS ref_asset_surrogate (
    canonical_asset_id INTEGER PRIMARY KEY,
    asset_id TEXT NOT NULL UNIQUE REFERENCES ref_asset(asset_id),
    created_at TEXT NOT NULL,
    evidence_json TEXT
);

CREATE TABLE IF NOT EXISTS ref_instrument_surrogate (
    canonical_instrument_id INTEGER PRIMARY KEY,
    instrument_id TEXT NOT NULL UNIQUE REFERENCES ref_instrument(instrument_id),
    created_at TEXT NOT NULL,
    evidence_json TEXT
);

CREATE INDEX IF NOT EXISTS idx_ref_listing_lifecycle
    ON ref_listing_event(venue_id, venue_symbol, valid_from, known_from);
