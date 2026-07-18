# Source note — Kraken

**Role:** BACKFILL_PRIMARY_CANDIDATE (spot)
**Audit date:** 2026-07-18

## Samples acquired
- OHLC 1h `XBTUSD` since 2025-01-01: 721 rows, sha ed2b3dba…; fields [time,open,high,low,close,vwap,volume,count].
- Trades `XBTUSD` since 2025-01-01: 1000 rows, sha a0d9c878…; fields [price,volume,time,side,ordertype,misc].

## Schema / semantics
- Pair keys are **prefixed** (`XXBTZUSD` for XBT/USD). Map to canonical `BTC-USD`.
- OHLC: unix-seconds UTC; 1h bars.
- Trades: float unix-seconds; side (b/s), ordertype (l/m), misc flags.

## Unit conventions
- **Volume is in the base asset (XBT)**, price in quote (USD). Watch for base/quote
  inversion when aggregating with Binance/OKX (which report volume in base too, but pair
  naming differs).

## Timestamp precision
Unix seconds UTC (float for trades). 2025-01-01 boundary confirmed present.

## Open question
- No-trade candle handling unverified: does Kraken emit a zero-volume OHLC bar for an
  interval with no trades, or omit it? Reconstruct bars from trades and diff against
  provider candles to settle this (Open Question 3).

## Licensing
Public REST usable for research; confirm redistribution clause.

## Gaps
- Bulk-file layout and no-trade interval semantics need explicit verification (planned).
