# FX-001 — Point-in-Time Stablecoin FX Readiness Report

**Ticket:** FX-001
**Status:** AWAITING_REVIEW
**Next ticket authorized:** NONE
**Next required actor:** Reviewer
**Date:** 2026-07-20

## 1. Repository Facts and Contradictions

### Implemented Contracts (accepted)
- RAW-001/002: Raw object writer + catalog with lexical path safety and `lstat` component verification for publication receipts.
- MAN-001: Immutable dataset manifest publisher. Manifests carry generic `dataset_type: str`, `schema.name`, `schema.version`, `schema.fingerprint`, source inputs (raw_object or dataset), transform, output files, row/byte counts, temporal coverage, quality.
- REF-001: Point-in-time asset and instrument master (bitemporal).
  - `AssetClass` enum (in `src/cryptofactors/reference/models.py`): `CRYPTO`, `FIAT`, `STABLE`, `DERIVATIVE_UNDERLIER`, `OTHER`.
  - `Asset` dataclass: `asset_id`, `asset_class`, `display_name`.
  - `Instrument`: `instrument_id`, `asset_id` (the traded asset), `venue_id`, `instrument_type`, optional `base_asset_id`, `quote_asset_id`.
  - `asset_id_for(*, asset_class: AssetClass, identity_key: str)` for stable/FIAT lookup.
  - Bitemporal windows (valid/known half-open), listing/migration events, alias resolution with manual ambiguity queue.
- BAR-001: Canonical bar publisher. Bars carry native `quote_volume` (in instrument quote asset) + `taker_buy_quote_volume`. No USD conversion. `dataset_type = "market_bars"`.
- CAT-001/001A, AUD-003: Generic catalog (dataset manifests, raw registration). SQLite for control metadata only (source, raw_object, dataset, ref_*, watermark, etc.). Observations in Parquet via manifests.
- Dataset identity: manifest-based `dataset_id = "ds_" + sha256(canonical_json(manifest_without_id))`. No mutable latest.
- No FX-specific table, dataset_type, or registered observations in sql/control_schema.sql or migrations 0001-0006.

### Planned but Not Implemented
- Architecture 01_DATA_ARCHITECTURE.md defines `stablecoin_fx` as core dataset type:
  > "Observed quote-to-USD conversion. Never assume USDT/USDC equals exactly one dollar in historical calculations."
- Required for quote-volume to USD in universe gating (architecture 01 §8), historical returns, etc.
- Risk D-04 (P0/Open in 09_RISK_REGISTER.md): "Stablecoin quotes assumed equal to USD" → control "Point-in-time stablecoin FX dataset".
- Mentioned in 00_SYSTEM_ARCHITECTURE.md, 07_IMPLEMENTATION_ROADMAP.md (Phase 2), but no implementation.

### Contradictions / Gaps
- Architecture and risk require PIT FX before quote-volume consolidation/universe/returns.
- Current bars preserve venue `quote_volume` (e.g. in USDT) with no FX layer or policy.
- REF has STABLE/FIAT classes and base/quote asset IDs on instruments, but no seeded "USD" FIAT asset or stable-to-USD FX observations registered.
- No source authority for reconstructable stablecoin market FX rates.
- Sprint-003/AUD-005 addressed kline quote_volume column semantics for bars, not FX normalization.

## 2. Source-Authority Matrix (Audited Statuses Only)

No FX source is accepted/audited for stablecoin quote-to-USD rates. All "not audited for FX" or absent from plans.

| Provider | Status (per repo) | Citation |
|----------|-------------------|----------|
| Binance public archives / kline | Audited for bars (klines include quote volume in quote asset). No FX rates or stable-to-USD. | 02_DATA_SOURCE_PLAN.md, AUD-005/RAW-002 records, BAR-001 |
| Bybit public API | Audited for perps/funding/trades. No FX. | 02_DATA_SOURCE_PLAN.md, BYB-001 |
| Kraken downloadable | Audited for spot OHLCVT. No FX rates. | 02_DATA_SOURCE_PLAN.md |
| OKX | Audited for derivatives/funding. No FX. | 02_DATA_SOURCE_PLAN.md |
| Coin Metrics | Listed as conditional reference metadata (market-cap/size); historical limits, vintages not primary for FX. | 02_DATA_SOURCE_PLAN.md (not audited for FX rates) |
| DefiLlama | Mentioned in task context; no entry in Phase 1/2 source plan as PIT FX source. Current-biased supply data only in external notes. | No audited PIT FX in 02_DATA_SOURCE_PLAN.md or accepted drops |
| Official issuer attestations (USDT/USDC) | Not in source plan; not market rates. | Absent |

Current bar sources provide venue quote volume only. No accompanying PIT USD FX dataset or raw FX objects registered.

## 3. Proposed Exact Parquet Observation Schema (Deterministic)

Proposed `dataset_type = "stablecoin_fx"`

Canonical schema (modeled on BAR-001 `_canonical_bar_schema` pattern; Parquet):

```python
pa.schema([
    ("stable_asset_id", pa.int64()),          # REF asset_id where asset_class=STABLE (e.g. USDT)
    ("target_asset_id", pa.int64()),          # REF asset_id where asset_class=FIAT (USD)
    ("observation_time", pa.int64()),         # event/quote time (UTC epoch us, per bar convention)
    ("source_publication_time", pa.int64()),  # when source published the rate
    ("system_acquisition_time", pa.int64()),  # when raw captured in this repo
    ("availability_time", pa.int64()),        # when FX became available for decision_time join
    ("rate", pa.decimal128(38, 18)),          # quote-to-target (e.g. USDT per USD), nullable
    ("source_id", pa.string()),               # e.g. "binance_spot", "defillama"
    ("source_dataset_id", pa.string()),       # input manifest or raw_object_id
    ("quality_flags", pa.string()),           # e.g. "depeg;low_liquidity" or null
])
```

- Nullability: rate nullable; others non-null where required by invariant.
- Units: rate is stable_asset per 1 target_asset (e.g. USDT/USD).
- Semantic invariant: rate reflects observed market conversion at observation_time; never assume =1.0.
- Canonical row order: sorted by (stable_asset_id, target_asset_id, observation_time, source_id).
- Partition path: e.g. stable_asset_id=.../target=USD/ (or by availability window).
- Dataset manifest dependencies: source raw/dataset IDs for the rates.
- Schema name/version: e.g. "stablecoin_fx" / "1".
- Transform: documented normalizer version + code_commit.
- Identity body for dataset: manifest without dataset_id, canonical JSON, sha256.

Observation identity: content hash of (stable_asset_id, target_asset_id, observation_time, source_id, rate, source_publication_time, ...) or surrogate + bitemporal.

Times: all UTC, stored as int64 epoch-microseconds (consistent with BAR-001 period/availability). Use `dt_to_iso` (fixed-width YYYY-MM-DDTHH:MM:SS.ffffffZ) for any manifest/JSON metadata.

Decimal: decimal128(38,18) for rate (matches bar volumes/prices).

## 4. Point-in-Time Policies (Exact, No Fills)

- **Observation vs times**: 
  - observation_time: market quote time of the rate.
  - source_publication_time: source's publish timestamp for that rate.
  - system_acquisition_time: repo raw capture time.
  - availability_time: when the rate is usable for as-of joins (max of above + processing).
- **Depegs**: rate != 1.0 (within tolerance documented in policy_version) at observation_time/availability_time. Flag explicitly; quarantine affected downstream volumes if policy requires.
- **Stale/missing**: If no observation with availability_time <= decision_time for the (stable, target) at required granularity, mark missing. No forward-fill or last-known carry. Use explicit "no_fx" or fail.
- **Revisions**: New observation or new dataset version supersedes; old manifests and derived calculations remain immutable via as-of.
- **Source disagreement**: Store per-source rows. Downstream policy (e.g. primary source or median of approved) chooses at join time. Record disagreement in quality_flags or separate reconciliation dataset.
- **As-of join**: For any decision_time, use FX row(s) with availability_time <= decision_time and observation_time closest <= decision_time (or policy window). Fail-closed if none.
- **Quarantine**: FX raw or failed normalization goes to quarantine with issue record. Never promoted.
- No silent haircuts/fills. All conversions must join explicit FX observation.

## 5. Integration Boundaries and Catalog Sufficiency

- **REF-001**: Use existing `asset_class=STABLE` and `=FIAT` for stable_asset_id / target_asset_id. Instruments already carry base/quote asset IDs. No new REF types needed for identity. "USD" as FIAT asset must be seeded if not present (distinguish capability vs actual registration).
- **BAR-001 / volume**: Keep native quote_volume. USD conversion is post-bar, using stablecoin_fx join on instrument.quote_asset (if STABLE) at decision/availability time.
- **MAN-001 / CAT**: Generic `dataset_type="stablecoin_fx"`, manifest for inputs/outputs sufficient for lineage, idempotency, supersession. No need for FX-specific SQLite table (SQLite = control only; observations = Parquet via manifests, per architecture 01).
- Generic catalog metadata (manifests, raw registration, dataset_input_*) is sufficient for control-plane invariants (provenance, versioning, quality). No SQL migration required unless a new control-plane metadata table (e.g. FX policy version registry) is justified separately from generic manifests.
- Downstream (universe, labels, returns): must join FX at PIT; current contracts do not yet define the join or "volume_usd" derived dataset.

## 6. Ordered Ticket Split (Smallest Steps)

Phase 1 (smallest, blocked until source): Source feasibility audit for PIT stablecoin FX rates.
- Inputs: existing architecture, REF-001 contracts, 02_DATA_SOURCE_PLAN.md, Sprint-003 source decisions.
- Outputs: audited list of candidate sources (e.g. Binance spot USDT pairs as proxy, or specific aggregator), with evidence of PIT reconstructability, revision behavior, raw capture feasibility.
- Boundaries: no code, no collection; just report + recommendation.
- Acceptance: exact citations, one recommended primary source or "none viable yet".
- Exact commands: same as current (pytest on focused tests if any, ruff, mypy, full suite, layer, repo-control).

Phase 2 (after source authority): ADR + schema + minimal normalizer (if source approved).
- Define exact schema (above), dataset_type, policies.
- If needed: control metadata only (no FX rows in SQLite).

Phase 3: Implementation of normalizer + publisher for one source + PIT join helper + tests.

## 7. Exact Recommendation (One Smallest Next Action)

**Source-feasibility audit for stablecoin FX rates (new ticket, e.g. FX-002).**

Rationale:
- No FX source is currently accepted/audited (per 02_DATA_SOURCE_PLAN.md and accepted drops).
- D-04 blocks Phase 2+ work; architecture names the need.
- REF-001 already provides STABLE/FIAT + base/quote IDs; generic catalog + Parquet sufficient.
- Any implementation must be blocked until source authority established (raw lineage, PIT, revisions).
- Select this over ADR or implementation: source facts first.

Do not authorize implementation, migration, or ADR until source feasibility complete.

## 8. Evidence Sources (All In-Repo)

- Architecture: 01_DATA_ARCHITECTURE.md (stablecoin_fx section, volume conversion), 00_SYSTEM..., 02_DATA_SOURCE_PLAN.md (no FX sources), 07_ROADMAP.md, 09_RISK_REGISTER.md (D-04), 11_LAYER...
- REF-001: src/cryptofactors/reference/models.py (AssetClass.FIAT/STABLE), store.py (asset_id_for, base/quote), REF-001_INTEGRATION.md + migrations/0006...
- BAR-001/MAN-001/CAT: bars.py (MARKET_BARS_DATASET_TYPE, quote_volume, generic dataset_type), manifests, control_schema.sql (no fx table).
- Source audits: Sprint-003/AUD-005 (kline quote volume only), RAW/BYB/BIN records.
- No stablecoin_fx tables, registered FX datasets, or accepted FX sources found.

All facts directly from repository content. No external assumptions. Generic catalog sufficient for observations; SQLite excluded for data rows.

---

**Governing documents for this report**: tickets/FX-001.md, REVIEW-0079, FX-001_JR_READINESS_TASK.md, REVIEW-0080, FX-001_JR_READINESS_CORRECTION_TASK.md
