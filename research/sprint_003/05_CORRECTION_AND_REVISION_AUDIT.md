# 05 — Correction and Revision Audit

**Sprint:** 003
**Research cutoff:** 2026-07-18

## Principle

Current metadata is **not** historical truth. Every source below can correct or replace
past observations. A research platform must store the retrieval timestamp and the source
version/commit alongside every object, and must treat later corrections as new information
rather than overwriting history.

## Per-source correction / revision behavior (from audit)

- **Binance archive** — real replacement register AUDITED this correction:
  `binance/binance-public-data` → `updates/2022-10-04_aggregate_trade_updates.csv` has format
  `File, Original File Checksum, New File Checksum` (e.g. BNBBTC-aggTrades-2018-01 old→new).
  Binance DOES replace historical files and publishes both checksums. The 2025-01-01 spot
  aggTrades provider `.CHECKSUM` sidecar was verified to **match** the locally computed
  SHA-256 exactly. Implication: backfill MUST validate provider CHECKSUM at acquisition and
  record both old and new checksums on replacement; never assume immutability.
- **Binance REST** — live, current-only; valid for incremental capture only.
- **Kraken** — bulk files are periodic snapshots; reconstructed bars from trades may differ
  from provider candles (no-trade interval handling unverified). Treat provider candles as
  the canonical reference and reconcile against reconstructed bars.
- **OKX** — funding `formulaType` and funding interval have changed over time (documented
  in OKX docs); `fundingTime` is authoritative but the *formula* applied at a past timestamp
  may differ from the current one. Store the formula/interval effective at each timestamp.
- **Bybit** — `fundingInterval` and `contractType` are explicit fields; historical funding
  history is cursor-paginated and reflects current definitions. Capture `fundingInterval`
  per instrument snapshot.
- **Coin Metrics v4** — server-side; the catalog reflects **current** availability ranges
  (per-metric `min_time`/`max_time`). Timeseries observations carry a `status` field that
  distinguishes `active`, missing, and unsupported. A metric's availability range can
  expand (backfill added) or be revised; the catalog snapshot timestamp must be stored.
- **DefiLlama** — TVL and emissions were recomputed server-side; history was not a fixed
  file. **CHANGED this correction:** the emissions API (`api.llama.fi/emissions/<token>`)
  now returns **HTTP 402** (paid plan) and the old SDK `emissions/adapters` path 404s. The
  free emissions/unlock bridge is gone; it is now CONDITIONAL on a paid plan. Pin any future
  adapter repo at an exact commit and record it.
- **Token unlocks (Tokenomist/Messari/DefiLlama emissions)** — schedule data is frequently
  revised (projections change). We **could not verify vintage preservation** for Tokenomist
  (unreachable). Assume current charts do **not** retain old information sets unless proven
  otherwise. On-chain vesting contracts are the only authoritative point-in-time source.
- **On-chain (node/explorer/Dune/Glassnode)** — block timestamps and indexer publication
  times differ; revisions/backfills change history. Not queried this audit; required for
  NET-01/DIL-01 publication-time audit.

## Required controls (design, not implemented this sprint)

1. Every stored object carries: `source`, `endpoint_or_path`, `request_params`,
   `retrieved_utc`, `sha256`, and (where applicable) `source_version`/`commit`/`checksum`.
2. Corrections create a new versioned object; never mutate an existing one.
3. For revision-prone series (Coin Metrics ranges, DefiLlama, unlocks), re-pull the catalog
   / adapter commit periodically and diff availability.
4. For formula/interval changes (OKX/Bybit funding), snapshot the effective parameters with
   each observation.

## What we could NOT verify

- Binance provider-replacement checksum exemplar (register unreachable).
- Tokenomist historical-schedule vintage preservation (host TLS-unreachable).
- Any on-chain publication-time vs block-time reconciliation (not queried).
