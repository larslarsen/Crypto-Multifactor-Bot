# Source note — OKX (FUND-003, corrected under REVIEW-0106)

**Environment:** captures 2026-07-21 (retained `/tmp/opencode/source_recheck_20260721/`) and
2026-07-22 (re-fetched `/tmp/okx_cap/`). All raw payloads preserved outside Git.

## Historical funding archive (module 3)

- URL pattern: `https://static.okx.com/cdn/okex/traderecords/swaprates/daily/YYYYMMDD/allswap-fundingrates-YYYY-MM-DD.zip?v=999`
- CSV columns: `instrument_name,funding_rate,funding_time` (no formulaType, no predicted/realized flag).
- `funding_time` is Unix epoch milliseconds (13-digit integer); documented as settlement time.
- Endpoint introduced September 2025 (per historical-data landing page).
- Object `Last-Modified` shows archives were replaced after their date (R01: 2026-02-02; R12: 2025-12-17).
  Last-Modified alone does NOT establish replacement/correction policy.

## REST API

- `GET https://www.okx.com/api/v5/public/funding-rate-history?instId=BTC-USDT-SWAP`
- Returns up to 3 months; response headers carry `ok-after` / `ok-before` window bounds.
- Fields: `formulaType` (noRate/withRate), `fundingRate` (predicted), `realizedRate` (actual settled),
  `fundingTime` (settlement time ms), `method`, `instType`.
- Archive CSV has no formulaType and no predicted/realized distinction — only a single `funding_rate`.

## Interval semantics

- Default 8h; variable 6h/4h/2h/1h for volatile altcoins (docs).
- 2026-07-19 archive distribution (by funding_time differences): 231 instruments at 8h, 194 at 4h,
  **1 at 2h**, **1 at 1h**.
- Formal rules (adjacent-event, cross-day, tolerance, frequency-transition encoding) are NOT documented.

## Formula transition (April 2025)

- REST docs define noRate (old) / withRate (new) but no archive carries formulaType.
- No official dated formula-change announcement captured. Transition boundary not verifiable from archives.

## Licensing

- OKX API Agreement §9.4 "Market Data — Non-Commercial Use and Redistribution Restrictions":
  restricts Market Data to non-commercial use; prohibits redistribution.
- Internal research acquisition and metadata retention are within non-commercial scope; redistribution is prohibited.

## Limitations

- 2022 archive (R01) has no proof of 2022 availability (Last-Modified 2026-02-02). Availability bound = 2026 onward.
- Replacement/correction behavior undocumented.
- R08–R10 exact POST request bodies not retained (re-fetch returns 429/param errors); request identity incomplete.
