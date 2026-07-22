# Source note — OKX (FUND-003, corrected under REVIEW-0106/0107/0108)

**Environment:** captures 2026-07-21 (retained `/tmp/opencode/source_recheck_20260721/`) and
2026-07-22 (re-fetched `/tmp/okx_cap/`). All raw payloads preserved outside Git.

## Historical funding archive (module 3)

- URL pattern: `https://static.okx.com/cdn/okex/traderecords/swaprates/daily/YYYYMMDD/allswap-fundingrates-YYYY-MM-DD.zip?v=999`
- CSV columns: `instrument_name,funding_rate,funding_time` (no formulaType, no predicted/realized flag).
- `funding_time` is Unix epoch milliseconds (13-digit integer); documented as settlement time.
- Endpoint introduction date is NOT stated on the historical-data landing page (the prior "September 2025"
  claim was unsourced and is removed).
- Object `Last-Modified` dates the current representation of the object (R01: 2026-02-02;
  R12: 2025-12-17). It does NOT prove replacement, and alone does not establish a
  replacement/correction policy.

## REST API

- `GET https://www.okx.com/api/v5/public/funding-rate-history?instId=BTC-USDT-SWAP`
- Returns up to 3 months; response headers carry `ok-after` / `ok-before` window bounds.
- Fields: `formulaType` (noRate/withRate), `fundingRate` (predicted), `realizedRate` (actual settled),
  `fundingTime` (settlement time ms), `method`, `instType`.
- Archive CSV has no formulaType and no predicted/realized distinction — only a single `funding_rate`.

## Interval semantics

- Mechanism article (R06B): cycles are 1h / 2h / 4h / 8h (interval factor N = 1,2,4,8; rate
  scaled by ÷N).
- API documentation (R04B): default 8h, "may be adjusted to higher frequencies such as 6 hours,
  4 hours, 2 hours, or 1 hour" — i.e. additionally mentions a possible 6h adjustment not present
  in the mechanism article.
- 2026-07-19 archive distribution (by funding_time differences): 231 instruments at 8h, 194 at 4h,
  **1 at 2h**, **1 at 1h** (no 6h observed in that archive).
- Formal rules (adjacent-event, cross-day, tolerance, frequency-transition encoding) are NOT documented.

## Formula transition (April 2025)

- REST docs define noRate (old) / withRate (new) but no archive carries formulaType.
- Official formula-change announcement captured (RFA):
  `https://www.okx.com/en-eu/help/okx-to-change-the-funding-rate-formula-for-perpetual-futures`
  — states the new formula rolled out in 3 batches from April 10, 2025.
- BTC transition-boundary archives around April 24, 2025 were UNAVAILABLE: all probed BTC
  transition-boundary dates around April 24 (20250422, 20250423, 20250424, 20250425, plus
  20250401/08/10/15/18/20/28/30) returned 404. Transition boundary not verifiable from archives.

## Licensing

- OKX API Agreement §9.4 "Market Data — Non-Commercial Use and Redistribution Restrictions":
  restricts Market Data to non-commercial use; prohibits redistribution.
- Evaluated for the INTENDED INTERNAL research use (acquisition of publicly available funding data
  and retention of metadata/hashes for internal non-commercial research): acquisition and metadata
  retention are within permitted non-commercial scope; redistribution is outside this gate and was not
  attempted.
- AMBIGUITY (G07 FAIL): whether §9.4's non-commercial restriction permits this specific internal
  research acquisition unambiguously is not expressly stated — gate fails on that ambiguity, not on
  absence of redistribution rights.

## Limitations

- 2022 archive (R01) has no proof of 2022 availability (Last-Modified 2026-02-02). Availability
  bound = 2026 onward (conservative; R02/R12 objects are post-endpoint).
- Replacement/correction behavior undocumented.
- R08–R10 exact POST request bodies not retained (re-fetch returns 429/param errors); request
  identity incomplete (G08 FAIL).
- Acquisition (retrieval) times recorded in the register are rounded capture timestamps, not
  independently retained precise times; this remains part of G08's failure until exact request
  identities/timestamps are captured.
