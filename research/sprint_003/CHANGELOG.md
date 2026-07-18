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
