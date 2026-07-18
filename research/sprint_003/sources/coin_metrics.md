# Source note — Coin Metrics (Community API v4)

**Role:** BACKFILL_PRIMARY_CANDIDATE (on-chain metrics) / REFERENCE_METADATA (catalog)
**Audit date:** 2026-07-18

## Samples acquired
- Catalog `assets` (no params): 5991 assets, sha a75dc20c…, 6.56 MB. Per asset, per-metric
  `frequencies[{frequency,min_time,max_time,community}]`.
- Availability confirmed: BTC `AdrActCnt` min 2009-01-03, SUSHI `AdrActCnt` min 2020-08-26
  (both max 2026-07-17). `SplyIssued` = ISSUED supply.

## Critical semantic finding
- **Issued native supply (`SplyIssued`) is NOT circulating float.** It includes locked /
  staked / unissued-per-schedule tokens. For `DIL-01` and float-based sizing, do not equate
  issued with circulating. Circulating/float and unlock series likely require Pro or a
  complementary source.
- Timeseries observations carry a `status` field that distinguishes **active / missing /
  unsupported** — missing is not the same as unsupported.

## API behavior (gotcha)
- v4 catalog `/catalog/assets` and `/catalog/asset-metrics` **reject** `page_size` and
  `limit` (HTTP 400). The no-param catalog call returns all 5991 assets in one payload.
- `/timeseries/asset-metrics` works but is param-format sensitive (bad date formatting →
  400). Pagination uses `next_page_key`.

## Timestamp precision
ISO UTC with **nanosecond** precision (e.g. `2009-01-03T00:00:00.000000000Z`).

## Correction / revision
Server-side; the catalog reflects **current** availability ranges. A metric's range can
expand (backfill added) or be revised; store the catalog snapshot timestamp.

## Licensing
Community API has usage limits; confirm non-redistribution of derived datasets. Broad
historical coverage / higher limits may require Pro/Atlas (separate procurement, SRC-012).

## Gaps
- Smaller-asset coverage and `community:true` quality flag behavior unverified (Open Q5).
- Pro tier necessity for float/unlock data not assessed.
