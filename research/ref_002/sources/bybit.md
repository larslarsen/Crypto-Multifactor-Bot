# REF-002 — Source Note: Bybit Instrument Event Feasibility

**Environment:** 2026-07-21 capture from `api.bybit.com`, `public.bybit.com`, and official Bybit docs.
**Status:** Evidence captured; recommendation is `NO_AUTHORITY`.

## Official Documentation Sources

- Instruments docs: `https://bybit-exchange.github.io/docs/v5/market/instrument`
  - Documents `launchTime`, `deliveryTime`, `status`, pagination, and `nextPageCursor`.
  - States `deliveryTime` is expired futures delivery time or perpetual delisting time.
- Enum docs: `https://bybit-exchange.github.io/docs/v5/enum#status`
  - Enumerates instrument `status` as `PreLaunch`, `Trading`, `Delivering`, and `Closed`.
  - Does not document `Settled` as a valid `instruments-info` status filter.
- Announcement docs: `https://bybit-exchange.github.io/docs/v5/announcement`
  - Documents `GET /v5/announcements/index` with `publishTime`, `type`, `tag`, `page`, and `limit`.
  - Does not document a symbol query.
- Legal source attempt: `https://www.bybit.com/en/help-center/article/Terms-of-Service`
  - Returned HTTP 403 `Access Denied` in this environment.
  - No explicit licensing provision for internal raw-evidence retention was captured.

## Captured Exemplars

- `BTCUSDT` linear perpetual listing exemplar:
  - `launchTime=1584230400000` (`2020-03-15T00:00:00Z`), `deliveryTime=0`, `status=Trading`.
  - Official archive `BTCUSDT2020-03-25.csv.gz` contains 2,693 rows spanning
    `2020-03-25T10:36:12.982200Z` through `2020-03-25T23:58:20.064700Z`.
- `BTCUSDU26` inverse futures scheduled-delivery exemplar:
  - `launchTime=1773388800000` (`2026-03-13T08:00:00Z`), `deliveryTime=1790323200000`
    (`2026-09-25T08:00:00Z`), `status=Trading`.
  - Retrieval predates delivery, so this branch is prospective only.
- Required settled branch:
  - Official `status=Settled` request is rejected with `retCode=10001` and `retMsg=params error: status invalid`.
  - No qualifying settled instrument candidate was returned from the required branch.
  - `BITUSD` is retained only as a supplemental `status=Closed` inverse-perpetual observation.
  - Symbol-specific `BITUSD` metadata returns `status=Closed` and `deliveryTime=1688108400000`
    (`2023-06-30T07:00:00Z`).
  - Archive listing includes `BITUSD2023-06-30.csv.gz` as the terminal listed object; that archive contains
    169 rows spanning `2023-06-30T00:04:30.954500Z` through `2023-06-30T06:56:32.034100Z`.

## Announcement Attempts

- Official delistings API attempt with `type=delistings&tag=Futures&limit=100&page=1` returned `total=0`.
- Broader `type=delistings&limit=100&page=1` returned 100 of 449 records with no `BITUSD` match on page 1.
- Result: no symbol-specific announcement publication time was captured for the required settled branch, and
  the supplemental `BITUSD` closed observation did not change that outcome.

## Net

Bybit supports deterministic prospective polling for instrument snapshots and provides archive edges that
corroborate economic validity. However, the required settled branch did not produce a candidate and the
captured official legal source did not establish permission for internal raw-evidence retention. The single
publishable recommendation is therefore `NO_AUTHORITY`.

## External Capture Paths

Exact raw bodies and headers are stored outside Git under `/tmp/ref_002_raw/http/` and are represented in
`research/ref_002/EVIDENCE_REGISTER.csv` (28 rows, 20 columns).
