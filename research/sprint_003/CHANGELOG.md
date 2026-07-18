# Sprint 003 Changelog

**Sprint:** 003 (data-source feasibility audit)
**Created:** 2026-07-18
**Research cutoff:** 2026-07-18
**Status:** data-source audit only; no empirical factor results; no factor validated

## Added (research/sprint_003/)

- `README.md` — scope, layout, control-plane note.
- `00_AUDIT_SCOPE_AND_METHOD.md` — vendors, per-object schema, acquisition approach, limits.
- `01_SOURCE_DECISION_REGISTER.csv` — 12 sources: decision (ACCEPT/CONDITIONAL/DEFER/
  REJECT) + architecture role + condition.
- `02_SOURCE_OBJECT_INVENTORY.csv` — 27 acquired objects with provider, role, endpoint,
  retrieval UTC, HTTP status, SHA-256, sizes, row counts, time ranges, notes (404/ERROR
  gaps included).
- `03_SCHEMA_AND_SEMANTICS_AUDIT.csv` — schema, timestamp precision, units, missing-interval
  semantics, revision/replacement behavior, status fields per source.
- `04_POINT_IN_TIME_REFERENCE_PLAN.md` — listing/delisting/delivery reconstruction with
  confidence classes (CONFIRMED_OFFICIAL / CONFIRMED_MARKET_DATA / INFERRED / CONFLICTED /
  UNKNOWN) and reconstructed exemplars.
- `05_CORRECTION_AND_REVISION_AUDIT.md` — per-source correction behavior; "current metadata
  is not historical truth" controls.
- `06_STORAGE_AND_COVERAGE_ESTIMATES.csv` — U25/U50/U100 × trades/1m bars/funding/
  instrument snapshots/order-book calibration with stated assumptions (no single-asset
  extrapolation).
- `07_VENDOR_TRIAL_REQUIREMENTS.md` — licensing/rate-limit/access actions per source.
- `08_RESEARCH_DATA_DECISIONS.csv` — audit findings mapped to Sprint 002 factor
  requirements / data-feasibility backlog (DF-01..DF-10).
- `09_OPEN_QUESTIONS.md` — 10 open questions.
- `CHANGELOG.md` — this file.
- `sources/` — 7 per-source notes: binance, kraken, okx, bybit, coin_metrics, defillama,
  token_unlocks.

## Source decisions (summary)

- ACCEPT: Binance live REST (SRC-001), Binance perp funding (SRC-003), Kraken (SRC-004),
  OKX (SRC-005), Bybit (SRC-006), Coin Metrics Community v4 (SRC-007), DefiLlama APIs
  (SRC-008).
- CONDITIONAL: Binance bulk zip (SRC-002 — 404 here), DefiLlama emissions adapters
  (SRC-009 — path moved), Messari (SRC-011 — 429/no key), On-chain node/explorer/Dune
  (SRC-012 — not queried).
- DEFER: Tokenomist (SRC-010 — TLS unreachable).

## Real acquisition results

- 27 objects retrieved HTTP 200 with SHA-256 recorded (Binance, Kraken, OKX, Bybit, Coin
  Metrics catalog + availability, DefiLlama chains/stablecoins/SDK commit).
- Gaps recorded honestly: Binance bulk zip 404; Tokenomist TLS-unreachable; Messari 404/429;
  DefiLlama ethereum adapter 404 at pinned commit.
- Key verifications: Binance Jan 1 2025 1m kline open_time = 1735689600000 ms UTC (no
  T-boundary shift); Bybit launchTime/deliveryTime/contractType fields present; Coin Metrics
  `SplyIssued` = issued (not circulating) supply; availability ranges BTC 2009 / SUSHI 2020.

## What was NOT changed

- Sprint 001 and Sprint 002 records frozen and unedited.
- `research/evidence/hypotheses.yaml` unchanged — `H-011` (DIL-01) and `H-007` (NET-01)
  remain DEFERRED/UNTESTED; this audit does NOT mark them research-ready.
- Active engineering ticket (GOV-001) untouched; no ingestion production code written; no
  commercial dataset purchased; no secrets committed; no large market-data objects committed.

## Verification performed

- All CSV column counts consistent; SHA-256 values present for every acquired object.
- Repository-control validator (GOV-001) remains PASS.
- Committed as one focused commit and pushed to origin/main.

## Correction pass — CHANGES_REQUIRED addressed (2nd Sprint 003 commit)

**Problem:** the original pass primarily tested live REST, not the required historical
backfill sources, and drew unsupported conclusions.

**Real historical-source acquisitions added:**
- Binance archive (`data.binance.vision`): BTCUSDT spot aggTrades 2024-12-31 (1,218,370 rows)
  and 2025-01-01 (653,485 rows); spot klines 1m 2025-01-01 (1,440 rows); USD-M perp
  aggTrades (726,612) and perp trades (1,804,361) 2025-01-01; funding monthly 2025-01 (94).
  Provider `.CHECKSUM` for 2025-01-01 **matches** local SHA-256 exactly.
- Binance replacement register (`binance/binance-public-data` → `updates/2022-10-04_aggregate_trade_updates.csv`)
  audited: real old→new checksum example (BNBBTC-aggTrades-2018-01).
- Bybit archive (`public.bybit.com/trading/`): BTCUSD inverse perp 2019-10-01 (4.0 MB gz),
  BTCUSDT linear perp 2020-03-25 (121 KB gz) with real schemas + unit divergence.
- Coin Metrics v4 **timeseries** (flat `data` array): btc/sushi SplyCur + AdrActCnt
  observations; `community:true` flag.

**Timestamp-precision boundary VERIFIED on archive files (not REST):** spot aggTrades
`transact_time` is 13-digit ms on 2024-12-31 and 16-digit µs from 2025-01-01.

**Corrections made:**
- Binance backfill now ACCEPT (wrong host was the original error).
- Removed invented role `BACKFILL_PRIMARY_CANDIDATE`; roles use only approved set.
- Coin Metrics issued supply = `SplyCur` (not `SplyIssued`); `SplyCur` ≠ circulating float
  (excluded = `SplyExNtv`); future unissued absent.
- Kraken/OKX historical bulk hosts unreachable (DNS) → CONDITIONAL; live REST retained as
  incremental only (Kraken OHLC 720-cap noted).
- DefiLlama emissions API now HTTP 402 (paid); old SDK adapter path 404 → CONDITIONAL.
- Bybit funding history capped at most-recent ≤100 (cursor None); pagination demonstrated on
  instruments-info. Real listing (BTCUSDT launchTime 2020-03-15) + delivery (BTCUSDU26
  deliveryTime) exemplars added with confidence classes.

**New files / updated:** `10_REVIEW_AND_ERRATA.md` (preserves + classifies first pass);
`02` adds `sample_status`/`limitation`/`superseded_by` and marks invalid rows; `01/03/04/05/
06/07/08/09` and all source notes corrected; README status + layout updated.

**Source decisions after correction:**
- ACCEPT (historical BACKFILL_PRIMARY or INCREMENTAL_PRIMARY): Binance archive+REST, Bybit
  archive+REST.
- ACCEPT (REFERENCE_METADATA): Coin Metrics catalog+timeseries, DefiLlama APIs.
- CONDITIONAL: Kraken bulk (host), OKX historical (host), DefiLlama emissions (paid), Messari
  (key), On-chain (keys), NET-01 publication-time bound.
- DEFER: Tokenomist (TLS).

**Still blocked / not upgraded:** DIL-01 (unlock vintage unavailable from any reachable free
source; DefiLlama now paid; Tokenomist TLS) and NET-01 (publication-time/revision unbounded).
Neither marked research-ready.

**Validation:** all CSVs consistent; hashes correspond to actual retrieved objects; timestamps
convert; decisions agree with evidence; no raw large dataset or secret committed.

