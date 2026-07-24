# DATA-010 — DEX Universe Asset OHLCV Backfill (U50+ Trading Assets)

**Priority:** P1
**Status:** DRAFT
**Dependencies:** DATA-007 (ACCEPTED), DEX-002 (ACCEPTED), UNIVERSE-004 (ACCEPTED), DATA-006 (ACCEPTED)
**Layer:** acquisition / dex
**Architecture:** extend existing `dex_multi_provider_fanout.py` fan-out engine; use DATA-007 `recommended_fanout` sources. **No LIVE. No Birdeye OHLCV.**

## Objective

Backfill DEX OHLCV for the **U50+ universe trading assets** (non-stablecoin) using the DEX-002 multi-provider fan-out, prioritizing assets by screening characteristics (liquidity, volume) to maximize rate-limit usage across the three fan-out data sources.

## Current State

DATA-006 backfilled only two Uniswap V3 USDC/USDT stablecoin pools on Arbitrum (~180 days via GeckoTerminal public API). The DEX-002 fan-out engine and provider infrastructure (`data/exp003_store/staged/dex_fanout/`) exist and have been tested in dry-run mode against mocked pool data but have never been run at scale against the actual U50+ trading asset universe. The DATA-007 rate-limit matrix provides per-source capacity estimates: ~720 pool-days/day from GeckoTerminal (primary), DexScreener for current snapshots (secondary), DefiLlama for liquidity/volume context (tertiary).

## Scope

### In scope

1. **U50+ DEX universe identification** — For each U50+ trading asset (BTC, ETH, SOL, XRP, ADA, AVAX, DOT, LINK, LTC, BCH, DOGE, UNI, AAVE, CRV, APE, NEAR, FIL, ARB, OP, SUI, SEI, WLD, PEPE), resolve the primary DEX pool addresses on the highest-liquidity chains (Ethereum mainnet, Arbitrum, Polygon) where the pair is quoted against USDC or USDT. These pool addresses become the `candidate_pools` input.

2. **Asset prioritization by screening characteristics** — Screen each pool using DexScreener (secondary) for current liquidity and 24h volume. Sort by a composite score (e.g. `sqrt(liquidity_usd * volume_24h_usd)`). High-score assets are backfilled first, ensuring rate-limit budget is spent on the most liquid, highest-signal assets. Configurable threshold: `--min-liquidity 50000 --min-volume 10000`.

3. **Multi-provider backfill per DEX-002 fan-out pattern**:
   - **GeckoTerminal (primary):** ~180-day OHLCV history per pool, ~6 req/min, ~720 pools/day.
   - **DexScreener (secondary):** gap-fill current snapshot when primary returns no record for a timestamp.
   - **DefiLlama (tertiary):** liquidity/volume context only; no OHLCV.

4. **Incremental watermark resume** — Reuse `ShardedWatermarkStore` from the dex_fanout module. Watermarks keyed by `(provider, chain, pool_address)`. Safe to re-run daily for incremental fills. Existing watermarks at `data/dex_fanout_watermarks.json`.

5. **Published dataset** — Publish a new canonical `dex_ohlcv_fanout` dataset per DEX-002 `PublishPlan` pattern. The existing stage directory `data/exp003_store/staged/dex_fanout/` is used for output.

6. **Report** `research/sprint_004/40_DEX_UNIVERSE_BACKFILL.json` with:
   - pools backfilled (address, chain, fee_tier, symbol)
   - record count per pool
   - provider breakdown (which sources filled each pool)
   - coverage start/end per pool
   - priority ranking (score, rank)
   - rate-limit incidents (429s, backoffs, timeouts)
   - rejected pools (screen failures with reasons)
   - total records published
   - pinned dataset id with catalog reconciliation

### Out of scope

- Stablecoin DEX pools (already covered by DATA-006)
- CEX backfill (DATA-008, DATA-009)
- Birdeye OHLCV (permanent constraint)
- LIVE / factor research
- Paid data sources
- On-chain data beyond DEX pool OHLCV (supply, unlocks, governance — DF-01/DF-02/DF-07)

## Assets to backfill (U50+ DEX pools)

For each U50+ trading asset (BTC, ETH, SOL, XRP, ADA, AVAX, DOT, LINK, LTC, BCH, DOGE, UNI, AAVE, CRV, APE, NEAR, FIL, ARB, OP, SUI, SEI, WLD, PEPE), resolve the primary DEX pool address on the chain with the deepest liquidity for the USDC or USDT pair. Minimum one pool per asset; multiple fee tiers where available (0.01%, 0.05%, 0.30%).

## Deliverables

1. Pool address resolution script or mapping for U50+ trading assets to DEX pool addresses on primary chains.
2. Priority scoring logic: screen → score → sort → backfill in rank order.
3. Extended `dex_multi_provider_fanout.py` (or a dedicated `backfill_dex_universe_pools.py`) supporting asset-priority sorting and the full U50+ pool set.
4. Published `dex_ohlcv_fanout` canonical dataset covering all screened U50+ pools.
5. Report `40_DEX_UNIVERSE_BACKFILL.json`.

## Acceptance (Jr)

1. `.venv/bin/python -m pytest tests/ -q --tb=short`
2. `.venv/bin/python -m ruff check src/cryptofactors/ scripts/`
3. `40_DEX_UNIVERSE_BACKFILL.json` present with ≥20 U50+ backfilled pools, per-pool coverage, priority ranking, and dataset id
4. Pools with zero liquidity/volume are rejected with documented screen failure
5. `python3 scripts/check_repo_control.py`

## Stop Condition

After Sr: AWAITING_REVIEW, Next ticket authorized: NONE.
