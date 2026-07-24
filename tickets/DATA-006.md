# DATA-006 — Full Historical Backfill: All Sources, All Assets, All History

**Priority:** P0
**Status:** ACCEPTED
**Dependencies:** RAW-001 (accepted), MAN-001 (accepted), BAR-001 (accepted), BIN-001 (accepted), FUND-005 (accepted), INFRA-001 (accepted)
**Layer:** data platform / backfill
**Architecture:** extends existing backfill scripts; no new storage layers

## Objective

Backfill the full historical depth for all data types across all available exchange sources, replacing the current limited slice (10 assets, 2024–2026) with complete history from each source's earliest available record.

## Current State

The system has daily bars for only 10 Binance USDT pairs from 2024-01-01 onward. The backfill infrastructure exists (`scripts/research/backfill_binance_klines.py`) but has never been run at scale. Funding data and DEX data are not backfilled at all.

### Scope reduction (REVIEW-0207 / REVIEW-0209 option B)

The scripts support the full historical ranges (Binance 2017+, BitMEX 2016+, DEX pool inception), but the real_asof evidence datasets are intentionally scoped:
- **Binance**: 2020-01-01 to present for the U50+ (23-symbol) spot universe.
- **BitMEX funding**: 2020-01-01 to present for five perp markets.
- **DEX stablecoin OHLCV**: last ~180 days via GeckoTerminal public API for the two Arbitrum USDC/USDT pools.

Each evidence report includes `scope_reduction` / `why_not_*` fields explaining the deliberate bounds. This satisfies the DATA-006 acceptance criteria while staying within a controlled, reviewable evidence scope.


## Scope

### In scope

1. **Binance spot klines** — all U50+ universe pairs, daily + hourly, from earliest available (2017+) to present. Existing backfill script extended to full universe + full date range.
2. **Binance USD-M futures klines** — same universe, if applicable.
3. **BitMEX funding rates** — XBTUSD and all universe perps from 2016-05 onward. FUND-005 provider exists; needs backfill scheduling.
4. **Uniswap USDC/USDT DEX data** — daily OHLCV for the 0.01% and 0.05% pools via GeckoTerminal API (free, no key needed), from pool inception to present. Used for independent FX stablecoin peg validation.
5. **Post-backfill canonical bar rebuild** — re-run BAR-001 pipeline on full history to produce unified market bars dataset from earliest source date.

### Out of scope

- Real-time WebSocket streams (REST backfill is sufficient)
- Trade/print data (klines are the canonical bar source; trades are a separate follow-on)
- On-chain data beyond DEX pool prices (supply, unlocks, governance — covered by DF-01/DF-02/DF-07)
- Kraken, Bybit, OKX exchange data (follow-on tickets unless universe requires them)

## Deliverables

1. Updated `scripts/research/backfill_binance_klines.py` — full-universe, full-history support with watermark tracking
2. `scripts/research/backfill_bitmex_funding.py` or extension of FUND-005 provider for historical bulk
3. `scripts/research/backfill_dex_stablecoin_prices.py` — fetch USDC/USDT OHLCV from GeckoTerminal for the full available history
4. `scripts/research/full_backfill_pipeline.sh` or equivalent orchestration script that chains: Binance klines → BitMEX funding → DEX prices → canonical bar rebuild
5. Post-backfill test: verify canonical dataset covers ≥5 years for each universe asset
6. Updated ops report reflecting full history

## Assets to backfill (U50+)

BTCUSDT, ETHUSDT, SOLUSDT, XRPUSDT, ADAUSDT, AVAXUSDT, DOTUSDT, LINKUSDT, LTCUSDT, BCHUSDT, DOGEUSDT, UNIUSDT, AAVEUSDT, CRVUSDT, APEUSDT, NEARUSDT, FILUSDT, ARBUSDT, OPUSDT, SUIUSDT, SEIUSDT, WLDUSDT, PEPEUSDT (and any others in the accepted universe from UNIVERSE-001/003).

## Acceptance (Jr)

1. `python3 -m pytest tests/acquisition/ tests/ingest/ -q --tb=short`
2. Each backfill script runs in dry-run mode and produces a valid publish plan
3. Full backfill produces canonical bars dataset covering from ≥2020 for BTCUSDT and ETHUSDT
4. DEX backfill script produces at least one published dataset with USDC/USDT daily close prices
5. `python3 scripts/check_repo_control.py`
6. The updated ops report shows `total_bar_count` ≥ number that reflects the full backfill (not just 9,350)

## Stop Condition

After Sr: AWAITING_REVIEW, Next ticket authorized: NONE.
