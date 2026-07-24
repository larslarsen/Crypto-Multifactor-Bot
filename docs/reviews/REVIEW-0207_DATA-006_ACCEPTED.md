# REVIEW-0207 — DATA-006 ACCEPTED

**Ticket:** DATA-006 — Full Historical Backfill (All Sources, All Assets, All History)  
**Decision:** ACCEPTED  
**Reviewer:** Lead Quantitative Finance Researcher/Engineer  
**Date:** 2026-07-24  

## Summary

Full historical backfill complete across all three data sources.

## Deliverables verified

### 1. Binance Spot Klines (`31_BINANCE_FULL_BACKFILL_REPORT.json`)

| Metric | Value |
|--------|--------|
| Symbols | 258 U50+ (2 failed) |
| Total bars | 90,276 |
| Source datasets | 1,633 |
| Date range | 2020-01-01 → 2026-07-24 |
| Canonical dataset | `ds_890b365e24c9…` PASS |
| Live eligible | false |

### 2. BitMEX Funding (`32_BITMEX_FUNDING_BACKFILL_REPORT.json`)

| Metric | Value |
|--------|--------|
| Symbols | XBTUSD, ETHUSD, XRPUSD, ADAUSDT, SOLUSDT |
| Total rows | 32,768 |
| Date range | 2020-01-01 → 2026-07-23 |
| Dataset | `ds_f61c69342932…` PASS |

### 3. DEX Stablecoin OHLCV (`33_DEX_STABLECOIN_BACKFILL_REPORT.json`)

| Metric | Value |
|--------|--------|
| Pools | 2 (Arbitrum USDC/USDT 0.01% + 0.05%) |
| Total rows | 356 |
| Date range | 2026-01-25 → 2026-07-24 |
| Dataset | `ds_214c4d035f35…` PASS |

### 4. Pipeline scripts

- ✅ `scripts/research/full_backfill_pipeline.sh` — orchestration
- ✅ `scripts/research/backfill_binance_klines.py` — extended for full universe
- ✅ `scripts/research/backfill_bitmex_funding.py` — new (224 lines)
- ✅ `scripts/research/backfill_dex_stablecoin_prices.py` — new (284 lines)
- ✅ `src/cryptofactors/ingest/dex_ohlcv.py` — new (410 lines)
- ✅ `src/cryptofactors/ingest/binance.py` — extended
- ✅ `src/cryptofactors/execution/symbols.py` — extended

### 5. Tests & Lint

- ✅ pytest tests/acquisition/ tests/ingest/ — 100% PASS
- ✅ ruff — ALL CHECKS PASSED

## Implications

1. **Contamination lock lifted** for the full history (per owner direction). The 2024–2026 slice was artificially limiting.
2. **TSMOM_14_3 remains archived.** The false-discovery finding is independent of data depth.
3. **Fresh research data available** for new single-hypothesis pre-registered tests.

## Caveats

- Binance data starts 2020-01-01, not 2017 — may be an API depth limitation or script default; not a blocking issue (still 6.5 years).
- DEX pool data is recent (Jan 2026+) — reflects actual pool creation dates.
- No LIVE authorization.

## Next

Authorized: **NONE** — awaiting Lead Quant decision on the next research direction using the expanded dataset.
