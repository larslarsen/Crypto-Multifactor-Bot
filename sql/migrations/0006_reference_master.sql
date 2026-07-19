-- REF-001: Point-in-time reference master (venues, assets, instruments, aliases)
-- Additive only. Runner owns the surrounding transaction.
-- Bitemporal half-open windows: valid_from/valid_to, known_from/known_to (UTC ISO-8601 TEXT).
-- NULL valid_to / known_to means open-ended.

PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS ref_venue (
    venue_id TEXT PRIMARY KEY,
    venue_code TEXT NOT NULL,
    display_name TEXT NOT NULL,
    venue_type TEXT NOT NULL
        CHECK (venue_type IN ('CEX', 'DEX', 'INDEX', 'OTHER')),
    created_at TEXT NOT NULL,
    UNIQUE (venue_code)
);

CREATE TABLE IF NOT EXISTS ref_asset (
    asset_id TEXT PRIMARY KEY,
    asset_class TEXT NOT NULL
        CHECK (asset_class IN (
            'CRYPTO', 'FIAT', 'STABLE', 'DERIVATIVE_UNDERLIER', 'OTHER'
        )),
    display_name TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS ref_instrument (
    instrument_id TEXT PRIMARY KEY,
    asset_id TEXT NOT NULL REFERENCES ref_asset(asset_id),
    venue_id TEXT NOT NULL REFERENCES ref_venue(venue_id),
    instrument_type TEXT NOT NULL
        CHECK (instrument_type IN (
            'SPOT', 'PERPETUAL', 'FUTURE', 'OPTION', 'INDEX', 'OTHER'
        )),
    base_asset_id TEXT REFERENCES ref_asset(asset_id),
    quote_asset_id TEXT REFERENCES ref_asset(asset_id),
    created_at TEXT NOT NULL
);

-- Versioned instrument attributes (contract terms); bitemporal.
CREATE TABLE IF NOT EXISTS ref_instrument_version (
    instrument_version_id TEXT PRIMARY KEY,
    instrument_id TEXT NOT NULL REFERENCES ref_instrument(instrument_id),
    version_seq INTEGER NOT NULL CHECK (version_seq >= 1),
    contract_spec_json TEXT NOT NULL,
    valid_from TEXT NOT NULL,
    valid_to TEXT,
    known_from TEXT NOT NULL,
    known_to TEXT,
    supersedes_version_id TEXT REFERENCES ref_instrument_version(instrument_version_id),
    evidence_json TEXT,
    CHECK (valid_to IS NULL OR valid_to > valid_from),
    CHECK (known_to IS NULL OR known_to > known_from),
    UNIQUE (instrument_id, version_seq)
);

CREATE INDEX IF NOT EXISTS idx_ref_instr_ver_instr
    ON ref_instrument_version(instrument_id, valid_from, known_from);

-- Aliases never auto-merge on text alone; resolution requires decision+knowledge time.
CREATE TABLE IF NOT EXISTS ref_alias (
    alias_id TEXT PRIMARY KEY,
    alias_text TEXT NOT NULL,
    alias_text_norm TEXT NOT NULL,
    venue_id TEXT REFERENCES ref_venue(venue_id),
    target_kind TEXT NOT NULL
        CHECK (target_kind IN ('ASSET', 'INSTRUMENT', 'VENUE')),
    target_id TEXT NOT NULL,
    valid_from TEXT NOT NULL,
    valid_to TEXT,
    known_from TEXT NOT NULL,
    known_to TEXT,
    confidence REAL NOT NULL DEFAULT 1.0
        CHECK (confidence >= 0.0 AND confidence <= 1.0),
    evidence_json TEXT,
    is_primary INTEGER NOT NULL DEFAULT 0 CHECK (is_primary IN (0, 1)),
    CHECK (valid_to IS NULL OR valid_to > valid_from),
    CHECK (known_to IS NULL OR known_to > known_from)
);

CREATE INDEX IF NOT EXISTS idx_ref_alias_norm
    ON ref_alias(alias_text_norm, venue_id, valid_from, known_from);

CREATE INDEX IF NOT EXISTS idx_ref_alias_target
    ON ref_alias(target_kind, target_id);

-- Listing lifecycle (list / delist / suspend / resume) at a venue.
CREATE TABLE IF NOT EXISTS ref_listing_event (
    listing_event_id TEXT PRIMARY KEY,
    instrument_id TEXT NOT NULL REFERENCES ref_instrument(instrument_id),
    venue_id TEXT NOT NULL REFERENCES ref_venue(venue_id),
    event_type TEXT NOT NULL
        CHECK (event_type IN ('LIST', 'DELIST', 'SUSPEND', 'RESUME')),
    valid_from TEXT NOT NULL,
    valid_to TEXT,
    known_from TEXT NOT NULL,
    known_to TEXT,
    evidence_json TEXT,
    CHECK (valid_to IS NULL OR valid_to > valid_from),
    CHECK (known_to IS NULL OR known_to > known_from)
);

CREATE INDEX IF NOT EXISTS idx_ref_listing_instr
    ON ref_listing_event(instrument_id, venue_id, valid_from);

-- Migrations / redenominations between instruments or assets.
CREATE TABLE IF NOT EXISTS ref_migration_event (
    migration_event_id TEXT PRIMARY KEY,
    event_type TEXT NOT NULL
        CHECK (event_type IN (
            'REDENOMINATION', 'CONTRACT_MIGRATION', 'ASSET_SPLIT', 'ASSET_MERGE', 'OTHER'
        )),
    from_kind TEXT NOT NULL CHECK (from_kind IN ('ASSET', 'INSTRUMENT')),
    from_id TEXT NOT NULL,
    to_kind TEXT NOT NULL CHECK (to_kind IN ('ASSET', 'INSTRUMENT')),
    to_id TEXT NOT NULL,
    ratio_num REAL,
    ratio_den REAL,
    valid_from TEXT NOT NULL,
    valid_to TEXT,
    known_from TEXT NOT NULL,
    known_to TEXT,
    evidence_json TEXT,
    CHECK (valid_to IS NULL OR valid_to > valid_from),
    CHECK (known_to IS NULL OR known_to > known_from),
    CHECK (
        (ratio_num IS NULL AND ratio_den IS NULL)
        OR (ratio_num IS NOT NULL AND ratio_den IS NOT NULL AND ratio_den != 0)
    )
);

CREATE INDEX IF NOT EXISTS idx_ref_migration_from
    ON ref_migration_event(from_kind, from_id, valid_from);

-- Manual ambiguity / resolution queue — never auto-resolved by ticker text alone.
CREATE TABLE IF NOT EXISTS ref_ambiguity_case (
    case_id TEXT PRIMARY KEY,
    alias_text TEXT NOT NULL,
    alias_text_norm TEXT NOT NULL,
    venue_id TEXT REFERENCES ref_venue(venue_id),
    decision_time TEXT NOT NULL,
    knowledge_time TEXT NOT NULL,
    status TEXT NOT NULL
        CHECK (status IN ('QUEUED', 'RESOLVED', 'REJECTED', 'DEFERRED')),
    candidate_json TEXT NOT NULL,
    resolution_target_kind TEXT
        CHECK (
            resolution_target_kind IS NULL
            OR resolution_target_kind IN ('ASSET', 'INSTRUMENT', 'VENUE')
        ),
    resolution_target_id TEXT,
    resolution_note TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    CHECK (
        (status = 'RESOLVED'
            AND resolution_target_kind IS NOT NULL
            AND resolution_target_id IS NOT NULL)
        OR (status != 'RESOLVED')
    )
);

CREATE INDEX IF NOT EXISTS idx_ref_ambiguity_status
    ON ref_ambiguity_case(status, created_at);

CREATE INDEX IF NOT EXISTS idx_ref_ambiguity_norm
    ON ref_ambiguity_case(alias_text_norm, venue_id);
