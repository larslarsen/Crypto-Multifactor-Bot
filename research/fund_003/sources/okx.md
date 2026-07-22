# Source note — OKX (FUND-003)

**Environment:** 2026-07-21 capture from `www.okx.com` and `static.okx.com`.

## Historical funding archive (module 3)

- OKX provides historical funding rate archives as ZIP files containing a single CSV per day.
- URL pattern: `https://static.okx.com/cdn/okex/traderecords/swaprates/daily/YYYYMMDD/allswap-fundingrates-YYYY-MM-DD.zip?v=999`
- CSV columns: `instrument_name,funding_rate,funding_time`
- `funding_time` is Unix epoch milliseconds (13-digit integer).
- Archives cover all swap instruments for that day.

## REST API

- Endpoint: `https://www.okx.com/api/v5/public/funding-rate-history?instId=BTC-USDT-SWAP`
- Returns up to 3 months of history.
- Response fields: `formulaType`, `fundingRate`, `fundingTime`, `instId`, `instType`, `method`, `realizedRate`
- `formulaType`: `noRate` (old formula) or `withRate` (new formula)
- `fundingRate`: predicted funding rate for upcoming settlement period
- `realizedRate`: actual settled funding rate
- `fundingTime`: settlement time, Unix timestamp in milliseconds
- Sign convention: positive = long positions pay short positions; negative = short pays long

## Interval semantics

- Default funding interval: 8 hours.
- For volatile altcoin swaps, OKX may adjust to 6h/4h/2h/1h intervals.
- Use difference between `fundingTime` and `nextFundingTime` to determine actual interval.
- Confirmed in 2026-07-19 archive: 196 instruments have 4-hour intervals (e.g. 0G-USDT-SWAP).

## Key findings

- Historical archive endpoint introduced September 2025 per documentation.
- 2022-05-01 archive object has `Last-Modified: 2026-02-02`, indicating replacement after 2022.
- ETag/Content-MD5 prove current object integrity but not historical immutability.
- OKX API terms restrict Market Data to personal, non-commercial use; redistribution prohibited.
- No funding interval field in instrument metadata; interval must be derived from funding_time differences.

## Limitations

- No proof the 2022 archive was available in 2022 (Last-Modified 2026-02-02).
- No provider changelog or version history for archive replacements.
- No conservative historical availability bound separate from local retrieval time.
- Redistribution prohibited by OKX API terms.
