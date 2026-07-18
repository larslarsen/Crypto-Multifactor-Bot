# Data Audit Plan

## Objective

Determine whether the locally held data can support a point-in-time, survivorship-aware, costed cross-sectional study.

No factor computation begins until Tier-0 checks pass.

## Current status

The legacy documentation claims broad CEX, DEX, on-chain, funding, and equity coverage. Because raw files are excluded from the public repository, every inventory row remains provisional until a local manifest with hashes is generated.

## Tier 0 — Materialization and provenance

For every file or API extract, record:

- immutable dataset ID;
- source and venue;
- instrument identifier;
- market type: spot, perpetual, futures, DEX pool, on-chain, macro;
- timeframe or event type;
- local path/object URI;
- byte size;
- SHA-256;
- row count;
- schema fingerprint;
- minimum and maximum event time;
- minimum and maximum availability time;
- acquisition time;
- collector version/commit;
- license or terms constraint.

**Gate:** no duplicate dataset IDs, no missing hashes, and every research input has a source and acquisition record.

## Tier 1 — Schema and timestamp integrity

Check:

- timestamp timezone and unit;
- interval-open versus interval-close convention;
- whether end timestamps are inclusive;
- sortedness;
- duplicate primary keys;
- expected interval gaps;
- impossible OHLC relationships;
- negative price or volume;
- volume units;
- quote currency and contract multiplier;
- decimal or token redenominations;
- stale-price runs;
- exchange outage periods;
- daylight-saving contamination in non-UTC sources.

**Gate:** all exceptions are either corrected by a versioned transform or explicitly excluded.

## Tier 2 — Cross-source consistency

For instruments appearing on multiple venues:

- compare log returns at synchronized times;
- compare close-price dispersion;
- compare volume scale;
- flag persistent symbol mismatches;
- detect unit errors and venue-specific outliers;
- retain venue prices separately before any consolidation.

A consolidated price must include the venue weights and source observations from which it was created.

## Tier 3 — Point-in-time symbol master

Create records for:

- canonical asset ID;
- venue instrument ID;
- base and quote assets;
- market type;
- listing and delisting times;
- contract launch and expiry;
- redenomination or migration;
- stablecoin, wrapped, leveraged-token, and synthetic flags;
- shortability/perpetual availability;
- fee tier;
- contract multiplier and funding interval.

**Gate:** no backtest joins on display ticker alone.

## Tier 4 — Availability semantics

For every non-price series, distinguish:

- observation period;
- event time;
- source publication time;
- first ingestion time;
- earliest lawful research availability.

Funding, on-chain, macro, and protocol metrics may not be joined by date alone.

## Tier 5 — Survivorship and coverage

At each historical decision date, quantify:

- number of listed assets;
- number with sufficient trailing history;
- number passing liquidity/completeness;
- number with spot execution;
- number with perpetual shortability;
- delistings in the next 7/30/90 days;
- missing return incidence.

A current symbol list must never be applied backward.

## Tier 6 — Market-data reliability

Exchange volume is not presumed truthful. Compare:

- cross-venue volume shares;
- price impact versus reported volume;
- zero-return and round-size distributions;
- venue regulation/reputation tier;
- known wash-trading indicators;
- spread and order-book consistency where available.

Use unreliable venue volume only as a sensitivity series, not as the sole universe gate.

## Tier 7 — Funding and derivatives

For each perpetual series:

- funding timestamp and interval;
- sign convention;
- payer/receiver convention;
- annualization method;
- mark/index price definition;
- missing funding periods;
- contract changes;
- whether a position held at the timestamp pays funding.

Backtests must book each historical cash flow, not merely use funding as a feature.

## Tier 8 — On-chain data

For each metric:

- chain and asset mapping;
- native versus tokenized asset;
- block time and finality;
- revision policy;
- data provider methodology;
- first availability;
- historical backfill/revision risk;
- unit and supply denominator.

On-chain inputs failing first-availability reconstruction remain Phase 2 research only.

## Deliverables from the local audit

1. `dataset_manifest.parquet`
2. `schema_registry.json`
3. `instrument_master.parquet`
4. `venue_master.csv`
5. `coverage_by_date.parquet`
6. `data_exceptions.csv`
7. `data_audit_report.md`
8. `raw_manifest.sha256`
9. point-in-time universe snapshots
10. a signed data-freeze record

## Acceptance gates

### Required for Phase 1

- CEX daily bars derived reproducibly from audited intraday or native daily data;
- point-in-time listing/delisting master;
- trailing quote-volume series;
- no unresolved timestamp-unit errors;
- delisted assets retained;
- realistic fee and funding records for the chosen implementation;
- deterministic hashes and schema versions.

### Required for Phase 2

- point-in-time market cap/circulating supply;
- on-chain availability timestamps;
- protocol taxonomy;
- DEX pool migration and liquidity histories.

## Stop conditions

Stop and repair data before modeling when:

- a source has unknown timestamp semantics;
- a symbol mapping is ambiguous;
- a volume unit changes without a corporate-action record;
- a delisted asset disappears from history;
- a feature is revised historically without vintage tracking;
- the same raw file changes without a new dataset ID.
