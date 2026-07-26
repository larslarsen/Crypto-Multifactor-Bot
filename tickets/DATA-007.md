# DATA-007 — Free DEX/CEX Source Capability & Rate-Limit Probe

**Priority:** P0  
**Status:** READY  
**Dependencies:** DATA-006 (ACCEPTED), UNIVERSE-002 (ACCEPTED), DEX OHLCV path (DATA-006)  
**Layer:** acquisition / research evidence  
**Architecture:** read-only probes + evidence artifact. **No LIVE. No Birdeye OHLCV.**

## Objective

Before expanding the universe, **measure** which free data sources we can actually run and at what rate. Output a decision-grade matrix so later tickets know capacity (pools/day, symbols/day, history depth).

## Hard constraints

1. **Birdeye free key = listing/creation events only.** Never call OHLCV/price/candle endpoints with that key (UNIVERSE-002).
2. **DEX “delist” = pragmatic death:** liquidity and/or volume below configurable thresholds for a sustained window (not an exchange delist message). Document thresholds as research config, not truth.
3. Prefer free tiers; paid only as a documented option in the matrix, not implemented here.
4. Secrets via env only; never commit API keys.

## Scope

1. **Probe matrix** (scripted, dry-run-safe where possible) for each candidate source:
   - Auth model (none / free key / env key name only)
   - Endpoints relevant to: (a) OHLCV/bars, (b) pool/token metadata, (c) listings (if any)
   - Observed or documented **rate limit** (RPS, daily CU, 429 behavior)
   - **History depth** for free OHLCV (e.g. Gecko ~180d)
   - Approx **CU/cost per call** if applicable
   - Can it support our screening fields (liquidity, volume, chain, address)?
2. **Minimum sources to evaluate:**
   - GeckoTerminal (existing client)
   - Birdeye (**listings only** — confirm cost of `new_listing`, do **not** probe bar endpoints)
   - At least **two additional free** OHLCV-capable or pool-stats sources (e.g. candidates: DefiLlama, DexScreener public, official chain subgraphs — pick what probes cleanly; document rejects)
   - Binance public klines (baseline CEX capacity for large universe)
   - BitMEX funding (baseline)
3. **Artifact** `research/sprint_004/35_FREE_SOURCE_RATE_LIMIT_MATRIX.json` (+ short markdown table optional under `research/sprint_004/` if useful):
   - per-source rows: `source_id`, `role` (`cex_bars` | `funding` | `dex_ohlcv` | `dex_listings` | `pool_stats`), `free_tier`, `rate_limit`, `history_depth`, `probe_status` (`ok`|`partial`|`fail`), `notes`, `birdeye_ohlcv_forbidden: true` on Birdeye row
   - `recommended_fanout`: ordered list of dex_ohlcv sources for DEX-002
   - `estimated_daily_capacity`: rough pools/symbols per day under polite limits
   - `live_eligible: false`
4. **Tests:** probe helpers unit-tested with mocks; no network required in CI.
5. **Do not** bulk backfill production catalogs in this ticket (probes may hit network once under `--no-dry-run` for measurement only).

## Out of scope

- Paid subscriptions  
- Birdeye OHLCV  
- LIVE / factor research  
- Full multi-provider production fan-out (→ DEX-002)

## Acceptance (Jr)

1. `.venv/bin/python -m pytest tests/ -q --tb=short` (or scoped acquisition/universe/ingest + new probe tests)
2. `.venv/bin/python -m ruff check src/cryptofactors scripts/`
3. `35_FREE_SOURCE_RATE_LIMIT_MATRIX.json` present with ≥5 sources and `recommended_fanout`
4. `python3 scripts/check_repo_control.py`

## Stop Condition

After Sr: AWAITING_REVIEW, Next ticket authorized: NONE.
