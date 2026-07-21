-- FEE-001: Point-in-time instrument fee schedules (bitemporal).
-- Additive only. Runner owns the surrounding transaction.
-- Rates stored as canonical decimal TEXT (never floating-point).
-- Half-open windows: valid_from/valid_to, known_from/known_to (UTC ISO-8601 TEXT).
-- NULL valid_to / known_to means open-ended.

PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS ref_fee_schedule (
    fee_schedule_id TEXT PRIMARY KEY,
    instrument_id TEXT NOT NULL REFERENCES ref_instrument(instrument_id),
    fee_tier_id TEXT NOT NULL,
    maker_fee_rate TEXT NOT NULL,
    taker_fee_rate TEXT NOT NULL,
    evidence_class TEXT NOT NULL
        CHECK (evidence_class IN ('OFFICIAL_SCHEDULE', 'ASSUMED_CONSERVATIVE')),
    valid_from TEXT NOT NULL,
    valid_to TEXT,
    known_from TEXT NOT NULL,
    known_to TEXT,
    supersedes_fee_schedule_id TEXT
        REFERENCES ref_fee_schedule(fee_schedule_id),
    evidence_json TEXT,
    CHECK (length(trim(fee_tier_id)) > 0),
    CHECK (valid_to IS NULL OR valid_to > valid_from),
    CHECK (known_to IS NULL OR known_to > known_from)
);

CREATE INDEX IF NOT EXISTS idx_ref_fee_schedule_lookup
    ON ref_fee_schedule(instrument_id, fee_tier_id, valid_from, known_from);

CREATE INDEX IF NOT EXISTS idx_ref_fee_schedule_instr
    ON ref_fee_schedule(instrument_id, valid_from, known_from);
