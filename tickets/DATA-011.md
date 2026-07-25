# DATA-011 — Survivorship-Bound CEX Quality Bar Panel (Binance First)

**Priority:** P0  
**Status:** ACCEPTED (REVIEW-0216)  
**Dependencies:** ARCH-002, UNIVERSE-006, DATA-005/DATA-008 patterns  
**Layer:** acquisition / bars  
**Architecture:** rebuild quality-cleared market_bars for symbols in the bound tradable
set. **No LIVE.**

## Objective

Produce a **PASS** (or PASS_WITH_WARNINGS) canonical daily bar dataset whose instrument
set is exactly the research tradable panel implied by UniverseBinding (Binance USDT
mapped names that are alive and screened) — not a disconnected static 10-pack.

## Scope

1. Map composite universe symbols → Binance pairs via translation maps (extend IDs as needed).
2. Backfill/refresh history for that set (reuse free Binance klines path).
3. Quality-clear (BAR-001 daily path) and pin dataset id for EXP-009.
4. Report coverage: bars per symbol, start/end, survivorship join rate.
5. **Do not** require full 2.7k multi-exchange universe (that is later UNIVERSE-005 phases).

## Out of scope

- MEXC/Kraken/Blofin
- DEX OHLCV
- Factor grid search

## Acceptance (Jr)

1. Published PASS dataset; instrument count ≥ current static map and documented  
2. Paper dry-run with ARCH-002 binding loads this dataset  
3. Gates + control check PASS  

## Stop Condition

AWAITING_REVIEW; next EXP-009 only after accept.
