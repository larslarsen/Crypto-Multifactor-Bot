# Source note — Bybit (CORRECTION: real archive + pagination)

**Role:** BACKFILL_PRIMARY (historical archive) + INCREMENTAL_PRIMARY (live REST)
**Audit date:** 2026-07-18 (correction pass)

## Real archive objects acquired (public.bybit.com/trading/<SYM>/)
- `BTCUSD` inverse perp 2019-10-01: 4.0 MB csv.gz, sha 61bb5a9f…; first row ts 1569974394.557895 (2019-10-01T23:59:54Z).
- `BTCUSDT` linear perp 2020-03-25: 121 KB csv.gz, sha cbca6933…; first row ts 1585180700.0647.

## Archive schema (CSV.gz)
Columns: `timestamp,symbol,side,size,price,tickDirection,trdMatchID,grossValue,homeNotional,foreignNotional`.
- `timestamp` = unix seconds (float).
- **Unit divergence (critical):** INVERSE `BTCUSD` → `size` is in contracts (~USD notional; homeNotional=11668), while LINEAR `BTCUSDT` → `size` is in base BTC (0.042) and `grossValue` is in satoshis (28133700000). Normalize before cross-venue aggregation.

## Live REST (incremental, retained)
- `instruments-info` pagination: real cursor returns a DISTINCT second page (page 2 begins 1000LUNCUSDT…). Pagination DEMONSTRATED.
- `funding/history`: **capped at the most-recent ≤100 events**; `nextPageCursor` is `None` even with older `startTime/endTime` windows. Multi-page funding history is NOT available via this endpoint (documented honestly; do not assume cursor pagination on funding).
- `instruments-info`: `launchTime`, `deliveryTime`, `contractType`, `fundingInterval`, `state`.

## Real point-in-time exemplars
- LISTING: `BTCUSDT` linear perp `launchTime` = 1584230400000 (2020-03-15); archive file 2020-03-25 corroborates. `CONFIRMED_MARKET_DATA`.
- DELIVERY: `BTCUSDU26` inverse futures `contractType=InverseFutures`, `deliveryTime=1790323200000` (>0) — contrasts perpetual `deliveryTime=0`. `CONFIRMED_MARKET_DATA`.

## Units summary
- Linear: volume base, turnover quote. Inverse: volume in contracts (not base).
- Funding interval explicit (`fundingInterval`); snapshot per instrument over time.

## Licensing
- Public S3 archive usable for research; review Bybit terms for redistribution.
