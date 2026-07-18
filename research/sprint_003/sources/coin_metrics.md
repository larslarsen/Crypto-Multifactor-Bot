# Source note — Coin Metrics (CORRECTION: real timeseries, correct metric)

**Role:** REFERENCE_METADATA (conditional for NET-01)
**Audit date:** 2026-07-18 (correction pass)

## Real timeseries acquired (v4)
- `btc` `SplyCur`,`AdrActCnt` 2025-01-01..01-05: 6 daily observations. `SplyCur`=19,804,167 on 2025-01-01.
- `sushi` `SplyCur`,`AdrActCnt` 2025-01-01..01-05: `SplyCur`=279,146,247 on 2025-01-01; `AdrActCnt`=304.
- `bonk` (limited-coverage): NOT in Community catalog → timeseries 400. Community coverage
  for micro-caps is limited (likely Pro-only). Recorded as a coverage gap.

## CRITICAL CORRECTIONS vs first pass
1. **Issued supply metric is `SplyCur`, NOT `SplyIssued`.** `SplyIssued` is unsupported in
   v4 timeseries (returns 400). Confirmed `SplyCur` = current issued supply.
2. **Timeseries returns a FLAT `data` array** — `[{asset, time, metric:value, ...}]` — NOT
   the nested `{asset, series:[{metric, values}]}` shape the first pass assumed. The first
   pass's "empty" timeseries was a parsing error, not missing data.
3. **`SplyCur` is ISSUED supply, not circulating float.** Coin Metrics also exposes
   `SplyExNtv` (excluded/locked supply). Future unissued supply is NOT in any supply metric.
   Distinguish: (a) issued native (`SplyCur`), (b) locked/staked issued (`SplyExNtv`),
   (c) circulating float (derived = issued − excluded, not a single field), (d) future
   unissued (absent). For DIL-01, float must be derived; do not equate `SplyCur` with float.
4. `community:true` flag present on these assets (community-tier data quality).

## API behavior (gotcha, retained)
- Catalog `/catalog/assets` and `/catalog/asset-metrics` reject `page_size`/`limit` (400);
  no-param call returns all 5991 assets.
- Timeseries rejects `limit` (use date windows; pagination via `next_page_key` when present).

## Availability ranges (from catalog)
- `btc`: `SplyCur` 2009-01-03 → 2026-07-17; `AdrActCnt` 2009-01-03 → 2026-07-17.
- `sushi`: `SplyCur` 2020-08-28 → 2026-07-17; `AdrActCnt` 2020-08-26 → 2026-07-17.
- Absence of an observation for an asset/metric = missing (not unsupported); distinguish via
  catalog `min_time`/`max_time`.

## Timestamp precision
- ISO UTC with nanosecond precision (e.g. `2009-01-03T00:00:00.000000000Z`).

## Correction / revision
- Server-side; catalog reflects CURRENT availability. Ranges can expand (backfill added) or
  revise. Store catalog snapshot timestamp.

## Licensing / NET-01 condition
- Community API has usage limits. NET-01 remains CONDITIONAL until publication-time vs
  block-time lag and revision/backfill behavior are bounded (requires on-chain cross-check,
  SRC-010).
