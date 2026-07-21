# FUND-001 — Binance Funding-Cashflow Readiness Report

**Ticket:** FUND-001
**Status:** AWAITING_REVIEW
**Next ticket authorized:** `NONE`
**Next required actor:** Reviewer
**Date:** 2026-07-21

## Recommendation
**SOURCE_EVIDENCE_REQUIRED**

No audited stablecoin/USD FX source exists yet. The existing `schemas/funding_cashflow.schema.json`
and Binance monthly-funding archive evidence alone are insufficient to publish deterministic
`funding_cashflows` observations. The schema is non-governing and contains fields whose semantics
are not supported by accepted repo contracts. Only the rate-event layer can be defined today;
cashflow must remain blocked.

## 1. Source-Semantics Matrix — `calc_time`, `funding_interval_hours`, `last_funding_rate`

See `research/fund_001/source_semantics_matrix.csv` for the exact per-field register.

Summary:
- `calc_time`: archive field is 13-digit ms UTC epoch (e.g. `1735689600015`). Observed type is
  integer epoch milliseconds. Defensible meaning is the scheduled funding-event reference timestamp
  used by Binance for bookkeeping, not yet proven to equal settlement time or mark-price time.
  Provider semantics are not documented in accepted repo evidence.
- `funding_interval_hours`: observed value `8` for the captured January 2025 monthly archive.
  Unit is hours. Defensible meaning is publication interval for captured rows. Whether this value
  can differ per instrument, time, or contract type is unknown from accepted evidence.
- `last_funding_rate`: observed value is numeric, quoted in instrument terms (e.g. `0.00010000`
  for perps; units are funding-rate decimal, not percent). Defensible meaning is the published
  rate for the interval ending at or near `calc_time`. Whether this is pre-rate or post-rate
  mark/index is not documented in accepted evidence.

## 2. Event vs Cashflow

The source provides funding-rate events. A realized cashflow requires position inputs that are not
present in the archive schema and are not authorized yet:
- position notional and sign (long/short payer/receiver);
- settlement asset and price basis;
- mark/index/notional formula;
- venue sign convention for the specific instrument/contract type.

Publishing a rate row under `funding_cashflows` without these inputs mislabels event as realized
cashflow. The current schema conflates the two by naming the dataset `funding_cashflows` and
including `long_cashflow_sign` without notional inputs.

## 3. Identifier Reconciliation with REF-001

Accepted REF-001 contracts (`src/cryptofactors/reference/models.py`):
- `AssetClass` includes `CRYPTO`, `FIAT`, `STABLE`, `DERIVATIVE_UNDERLIER`, `OTHER`.
- `Instrument` uses string surrogate IDs (`instrument_id: str`, asset_id: str, venue_id: str).
- `InstrumentVersion` carries contract spec, bitemporal window, and supersedes chain.
- `ListingEvent`, `AliasRecord`, and bitemporal windows are supported.

The existing schema’s integer `instrument_id` conflicts with accepted REF-001 string surrogate IDs.
`venue_id` in the schema is correctly typed as string, but its domain is not referenced from an
accepted venue master. Any implementation must use accepted REF instrument/venue identifiers, not
the currently proposed integer.

## 4. Time Semantics

Separate four times:
- `funding_time` / `calc_time`: provider event timestamp (currently ms epoch).
- `source_publication_time`: not present in archive; live REST does expose a published-time field.
- `system_acquisition_time`: raw capture time; not present in the current schema.
- `availability_time`: earliest time this row may influence a strategy decision. Not present.

Unknowns that must remain unknown:
- whether `calc_time` equals mark-price time or settlement transfer time;
- intra-instrument settlement latency differences.

These unknowns block implementation.

## 5. Coverage, Replacement, Corrections, Quarantine

- Binance archive evidence confirms real historical replacement: provider publishes
  `updates/YYYY-MM-DD_aggregate_trade_updates.csv` with old/new checksums. Funding archives may
  receive similar updates. Backfill must validate provider CHECKSUM per object and retain old/new
  checksums on replacement.
- Missing events: a failed funding transmission on the exchange side is not observable from archive
  alone; absence of a row does not imply zero rate.
- Corrections: a new dataset version supersedes old; old manifests and derived rows remain
  immutable via as-of joins.
- The schema currently lacks `quality_flags`, `source_publication_time`, `system_acquisition_time`,
  and `availability_time`. These are required before publication.

## 6. Proposed Non-Governing Observation Identity

Non-governing proposal only; non-governing until source evidence and implementation review pass.

- `dataset_type`: `funding_cashflows`
- Schema name/version: `funding_event` / `1`
- Canonical fields:
  - `instrument_id`: string REF-001 instrument_id
  - `venue_id`: string REF-001 venue_id
  - `funding_time_us`: int64 epoch microseconds, event timestamp
  - `source_publish_time_us`: int64 epoch microseconds, nullable
  - `system_acquisition_time_us`: int64 epoch microseconds
  - `availability_time_us`: int64 epoch microseconds
  - `funding_rate`: decimal128(38,18), nullable
  - `funding_interval_hours`: int64
  - `long_cashflow_sign`: int8 enum {-1, 1}, nullable
  - `notional_base`: decimal128(38,18), nullable
  - `notional_quote`: decimal128(38,18), nullable
  - `settlement_asset_id`: string REF-001 asset_id, nullable
  - `mark_price`: decimal128(38,18), nullable
  - `index_price`: decimal128(38,18), nullable
  - `source_dataset_id`: string manifest dataset_id
  - `quality_flags`: string[], nullable
- Deterministic sort: `(instrument_id, funding_time_us, source_dataset_id)`
- Partition path: `venue_id=.../year=YYYY/month=MM`
- Raw/manifest lineage: source archive zip manifest → dataset manifest → this dataset
- Quality states: `PASS`, `PASS_WITH_WARNINGS`, `QUARANTINED`
- Failure policy: quarantined if schema fields missing or notional/settlement inputs absent when
  cashflow rows are emitted.

`rate_direction` is not applicable here; funding rate is signed rate, not FX USD conversion.
Do not add stablecoin-FX conversion inputs here; FX remains blocked.

## 7. Native Inputs and Layer Boundaries

- Preserve native settlement currency (venue quote asset for perps) and native cashflow inputs.
  Do not invent a USD conversion inside this layer.
- Carry forward FX-002 acceptance: `FX-002` is accepted with recommendation `NONE`; stablecoin-FX
  implementation remains blocked. Any USD-denominated cashflow view must be derived downstream
  after FX source authority is established.

## 8. Catalog Sufficiency and New Boundaries

Accepted RAW/MAN/REF/catalog boundaries are sufficient for event-only publication:
- RAW object registration, MAN-001 dataset manifests, CAT-001 catalog SQLite, and existing
  reference assets/instruments cover event lineage, identity, and as-of availability.
- A new public contract or layer boundary is required before cashflow rows: an ADR defining
  position/notional/settlement/sign semantics, stablecoin-FX conversion policy, and price basis.
  Do not write this ADR in this readiness ticket.

## 9. Records and State Transition

- `tickets/FUND-001.md`: set to `AWAITING_REVIEW`, record recommendation `SOURCE_EVIDENCE_REQUIRED`.
- `docs/handoff/CURRENT_TASK.md`: state `AWAITING_REVIEW`, next actor `Reviewer`, next ticket `NONE`.
- `docs/reviews/FUND-001_READINESS_REPORT.md`: this document.
- `docs/reviews/FUND-001_SEMANTICS_MATRIX.md`: source-semantics matrix.
- `docs/reviews/FUND-001_CONTRACT_MATRIX.md`: platform-contract matrix.
- `docs/engineering/IMPLEMENTATION_BACKLOG.csv`: FUND-001 `AWAITING_REVIEW`.
- `README.md`: FUND-001 listed as `AWAITING_REVIEW`.

## Acceptance Command Evidence

`python3 scripts/check_repo_control.py`
Repo control check: PASS

## 10. Stop Condition

Commit and push the readiness records. Return control to Reviewer. Retain `Next ticket authorized:
NONE`. Do not begin implementation, schema migration, ADR, or source requests.
