-- REVIEW-0225: venue listings are stable identities distinct from lifecycle events.
CREATE TABLE IF NOT EXISTS ref_venue_listing (
    listing_id TEXT PRIMARY KEY,
    venue_id TEXT NOT NULL REFERENCES ref_venue(venue_id),
    instrument_id TEXT NOT NULL REFERENCES ref_instrument(instrument_id),
    venue_symbol TEXT NOT NULL,
    created_at TEXT NOT NULL,
    evidence_json TEXT,
    UNIQUE (venue_id, venue_symbol)
);

ALTER TABLE ref_listing_event ADD COLUMN listing_id TEXT
    REFERENCES ref_venue_listing(listing_id);

CREATE INDEX IF NOT EXISTS idx_ref_listing_event_listing_lifecycle
    ON ref_listing_event(listing_id, valid_from, known_from);
