# FX-001 — Point-in-Time Stablecoin FX Readiness Report

**Ticket:** FX-001
**Status:** AWAITING_REVIEW
**Next ticket authorized:** NONE
**Next required actor:** Reviewer
**Date:** 2026-07-20

## 1. Repository Facts and Contradictions

### Implemented Contracts (accepted)
- RAW-001/002: Raw object writer + catalog with lexical path safety and `lstat` component verification for publication receipts.
- MAN-001: Manifests for dataset identity and lineage.
- REF-001: Reference master for assets/instruments with stable IDs, alias resolution, listing events.
- BAR-001: Canonical bars (OHLC + quote_volume, taker_buy_quote_volume) per instrument/venue/timeframe.
- CAT-001/001A, AUD-003: Catalog, audit, and control schemas (SQLite control + Parquet canonical).
- Dataset identity is manifest-based with `dataset_id = "ds_" + sha256(...)`.
- No mutable "latest"; everything is versioned/superseded.

### Planned but Not Implemented
- `stablecoin_fx` dataset explicitly defined in architecture:
  > "Observed quote-to-USD conversion. Never assume USDT/USDC equals exactly one dollar in historical calculations."
- Used for:
  - Converting venue `quote_volume` to USD in liquidity/universe consolidation.
  - Any historical price/volume/return calculations.
- Risk D-04 (P0/Open): "Stablecoin quotes assumed equal to USD" with control "Point-in-time stablecoin FX dataset".
- Mentioned in:
  - 01_DATA_ARCHITECTURE.md (as core dataset type alongside bars, funding, fees)
  - 00_SYSTEM_ARCHITECTURE.md (in canonical snapshots)
  - 07_IMPLEMENTATION_ROADMAP.md (Phase 2 exit criteria)
  - 09_RISK_REGISTER.md
- No persistent schema, table, or dataset_type for `stablecoin_fx` in:
  - sql/control_schema.sql
  - sql/migrations/ (0001–0006 cover source, raw_object, dataset, reference_master, evidence, etc.; no fx table)
  - No source_id, raw_object, or dataset registered for stablecoin FX.

### Contradictions
- Architecture and risk register require point-in-time stablecoin FX before universe, quote-volume consolidation, or net returns.
- Current canonical bars store raw `quote_volume` (venue quote currency) but no FX conversion layer or policy.
- No source authority, observation-time/availability-time contract, or revision model defined for FX rates.
- Sprint-003 (and AUD-005 corrections) addressed Binance kline quote_volume column semantics (index 7 vs 8) and runner, but did not address stablecoin normalization of those volumes.

## 2. Source-Authority Matrix

No stablecoin-FX source is currently authorized or ingested.

| Provider | Historical Depth | Observation Time | Availability Time | Revisions | Raw Capture | Licensing | Status |
|----------|------------------|------------------|-------------------|-----------|-------------|-----------|--------|
| Binance public (klines) | Good for spot/perps | Event time in kline | File publish time | Corrections exist | Full archives registered via RAW | Public | No FX rates |
| Bybit | Good perps | Event | Incremental | Revisions possible | API responses stored | Public | No FX |
| Coin Metrics | Long for some | As-of | Vintages limited | Provider revises | Not primary for FX | Varies | Deferred in plans |
| DefiLlama | Stablecoin focus | As-of | Current bias | Frequent updates | Not raw-captured for PIT FX | CC0-ish | No PIT capture |
| Kraken | Spot | Good | Good | Low | Downloads | Public | No FX rates |
| Official stablecoin issuers (USDT/USDC attestations) | Limited history | Not market rates | - | - | - | - | Not suitable for market FX |

Current bar sources provide `quote_volume` in the quote asset (e.g. USDT), but no accompanying point-in-time USD conversion dataset.

## 3. Proposed Minimal Typed Observation / Dataset Identity

Recommended observation row (for a `stablecoin_fx` dataset):

- `fx_id` (stable surrogate or hash)
- `stablecoin_asset_id` (e.g. USDT asset)
- `target_currency` ("USD")
- `observation_time` (event/quote time)
- `availability_time` (when the rate became known in the system)
- `venue_or_source_id` (e.g. "binance", "defillama", "onchain_oracle")
- `rate` (Decimal, quote-to-USD)
- `source_dataset_id` / `raw_object_id`
- `policy_version`
- `confidence_class` or quality flag
- `depeg_flag` (boolean or severity)

Dataset manifest would include source inputs (raw stablecoin price objects), transform, schema version.

Parquet schema: partitioned by decision/availability windows, with stable identifiers.

Deterministic identity for the dataset (manifest hash) and for observations (content-addressed or surrogate + times).

## 4. Point-in-Time Policies

- **Depegs**: Must be observable as rate ≠ 1.0 at the observation/availability time. Never backfill with 1.0. Quarantine or flag affected bars/volumes.
- **Stale/missing**: Explicit null or "missing" with reason; do not forward-fill. Use last-known only under documented conservative policy with version.
- **Source disagreement**: Store multiple observations; downstream chooses via policy (e.g. median of approved sources, or primary + deviation flag).
- **Quarantine**: Failed FX objects go to quarantine/ with issue records; do not promote to canonical FX dataset.
- **Fail-closed**: Downstream (universe, volume_USD, returns) must fail closed or apply explicit haircut if no valid FX observation for the decision time.
- No assumption that any stablecoin == 1.0 USD at any historical point without an observed rate at the correct as-of.

## 5. Integration Boundaries

- **Reference assets/instruments (REF-001)**: Stablecoins are assets; FX is a separate cross-rate observation between stablecoin asset and USD (treated as synthetic or reference currency).
- **Canonical bars (BAR-001)**: Bars keep native `quote_volume`. USD conversion happens at derived/universe layer using `stablecoin_fx` at the appropriate point-in-time.
- **Manifests / catalog (MAN-001, CAT)**: FX observations would be a first-class dataset type with its own manifests, inputs (raw price objects), and supersession.
- **Universe / labels**: Liquidity gating must use point-in-time converted volume; stablecoin FX is a prerequisite input.
- **Downstream**: Any quote-volume to USD, or price in USD, must join through the FX dataset at decision/availability time.

Current contracts do not yet define the FX dataset type or join semantics.

## 6. Required Next Artifacts

- ADR for stablecoin FX dataset identity, schema, and PIT semantics (highly likely required).
- SQL migration for control tables (fx_observation or equivalent) and any reference for stablecoins-as-assets vs USD.
- Source audit ticket for at least one primary provider of reconstructable stablecoin market rates (e.g. Binance spot USDT/USDC pairs treated as FX, or dedicated oracle/aggregator with PIT guarantees).
- Clarification on whether "USD" is a first-class asset or implicit reference currency in REF.
- Architecture update to 01/00 if the `stablecoin_fx` section needs more precision on observation vs availability time.

No current source drop or raw capture for FX rates exists in the audited Phase 1/2 sources.

## 7. Concrete Implementation Split, Acceptance-Test Matrix, Gates

**Minimal source task (if authorized later)** would cover:
- One or more stablecoin FX sources (e.g. Binance USDT-USD pairs or aggregator with raw).
- Normalizer producing canonical `stablecoin_fx` observations.
- Registration via RAW + catalog.
- Point-in-time join helper or view for volume_USD.

**Acceptance test matrix (high level)**:
- Depeg observation at exact time is retrievable and not 1.0.
- Bar quote_volume converted with contemporaneous FX matches expected.
- Missing FX at decision time causes fail-closed or documented conservative path.
- Revisions in source produce new dataset version, old calculations unchanged.
- Universe volume uses PIT FX, not latest.

**Exact gates (once implementation authorized)** would extend existing:
- PYTHONPATH=src uv run pytest tests/test_fx.py -q --tb=short (or equivalent)
- Full ruff, mypy scoped, pytest suite, layer imports, repo control.

**Explicit excluded scope (readiness phase)**: No code, no migrations, no data collection, no ADR yet.

## 8. Recommendation

**Authorize a smallest source-audit + schema ticket** (or ADR-first) rather than keeping FX-001 blocked.

Rationale:
- D-04 is P0 and blocks all quote-volume, universe, and return work.
- Architecture already names the dataset and its invariant.
- Current bar contracts are ready to consume it (they preserve raw quote_volume).
- No existing source authority or schema means any implementation would invent contracts — hence the readiness step was correct.

Next minimal step: reviewer-authorized ADR or source-plan addition + one primary PIT-stablecoin-FX source audit. Do not proceed to full FX-001 implementation without that.

---

**Evidence sources inspected** (all in-repo):
- docs/architecture/01_DATA_ARCHITECTURE.md, 00_SYSTEM_ARCHITECTURE.md, 02_DATA_SOURCE_PLAN.md, 07_IMPLEMENTATION_ROADMAP.md, 09_RISK_REGISTER.md, 11_LAYER_BOUNDARIES.md
- sql/control_schema.sql + migrations/
- tickets/FX-001.md, RAW-00*, REF-001, BAR-001, MAN-001, CAT-*, AUD-*
- Sprint-003 / AUD-005 records (quote volume semantics only)
- No stablecoin_fx tables, sources, or datasets found.

All facts are direct repository content. No external assumptions added.
