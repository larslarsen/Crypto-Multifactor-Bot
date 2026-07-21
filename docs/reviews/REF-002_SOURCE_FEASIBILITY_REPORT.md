# REF-002 — Bybit Instrument Event Source Feasibility Report

**Ticket:** REF-002
**Status:** ACCEPTED - NO AUTHORITY (REVIEW-0102)
**Next ticket authorized:** `NONE`
**Next required actor:** Reviewer
**Date:** 2026-07-21

## Recommendation
**NO_AUTHORITY**

Official Bybit sources still fall short of any publishable authority for REF-002. Historical event
authority fails because Bybit does not expose a documented inverse `status=Settled` filter, only
current-status snapshots such as `Closed`, and bounded official announcement attempts did not recover a
symbol-specific publication time for the required settled branch. Prospective-only authority also fails
because the single captured official legal source returned HTTP 403 and did not establish permission for
the intended internal raw-evidence retention.

## 1. Bounded Evidence Summary

### BTCUSDT listing exemplar
- Official `instruments-info` for `BTCUSDT` returns `contractType=LinearPerpetual`, `status=Trading`,
  `launchTime=1584230400000` (`2020-03-15T00:00:00Z`), `deliveryTime=0`, and `fundingInterval=480`
  minutes.
- Official trade archive `BTCUSDT2020-03-25.csv.gz` has 2,693 rows spanning
  `2020-03-25T10:36:12.982200Z` through `2020-03-25T23:58:20.064700Z`.
- Conclusion: `launchTime` is usable as official listing metadata; the 2020-03-25 archive corroborates
  that the instrument existed by that date without over-claiming first trade as the exact listing event.

### BTCUSDU26 scheduled delivery exemplar
- Official inverse `instruments-info` for `BTCUSDU26` returns `contractType=InverseFutures`,
  `status=Trading`, `launchTime=1773388800000` (`2026-03-13T08:00:00Z`), and
  `deliveryTime=1790323200000` (`2026-09-25T08:00:00Z`).
- Retrieval time is `2026-07-21`, so `BTCUSDU26` is a scheduled future-delivery exemplar only. It is not
  evidence of a completed historical delivery.

### Required settled branch and supplemental closed observation
- Official query `category=inverse&status=Settled&limit=1000` returns HTTP 200 with `retCode=10001` and
  `retMsg="params error: status invalid"`.
- Official enum/docs captures enumerate valid instrument `status` values as `PreLaunch`, `Trading`,
  `Delivering`, and `Closed`; `Settled` is not documented for `instruments-info`.
- No qualifying settled instrument candidate was returned from the required branch.
- Official fallback query `category=inverse&status=Closed&limit=1000` returns 48 qualifying inverse
  instruments with positive `deliveryTime < retrieval_time`. The lexicographically first symbol is
  `BITUSD`, which is retained only as a supplemental `Closed` inverse-perpetual observation.
- Symbol-specific `BITUSD` metadata returns `contractType=InversePerpetual`, `status=Closed`,
  `launchTime=1636934400000` (`2021-11-15T00:00:00Z`), and `deliveryTime=1688108400000`
  (`2023-06-30T07:00:00Z`).
- Official archive listing `public.bybit.com/trading/BITUSD/` includes `BITUSD2023-06-30.csv.gz` as the
  terminal listed object. That archive has 169 rows spanning `2023-06-30T00:04:30.954500Z` through
  `2023-06-30T06:56:32.034100Z`.
- Conclusion: the fallback `Closed` snapshot plus archive edge support only a supplemental closed/delisted
  perpetual observation. They do not satisfy the required settled branch and do not reconstruct historical
  known-time.

### Announcement attempt
- Official announcement docs capture `GET /v5/announcements/index` with `publishTime`, but no symbol query.
- `type=delistings&tag=Futures&limit=100&page=1` returns `total=0`.
- Broader `type=delistings&limit=100&page=1` returns 100 of 449 records with no `BITUSD` match on page 1.
- Conclusion: bounded official announcement retrieval did not recover a symbol-specific publication time for
  the required settled branch.

### Licensing / terms
- Official Bybit legal-source attempt:
  `https://www.bybit.com/en/help-center/article/Terms-of-Service` returned HTTP 403 `Access Denied` in this
  environment.
- No explicit official licensing clause was captured that establishes permission for the intended internal
  raw-evidence retention.
- Conclusion: licensing remains unknown and G07 fails literally.

## 2. Gate Results

The complete gate classification is in `research/ref_002/decision_matrix.csv` and is reproduced here:

| Gate | gate_label | Status | Blocking |
|---|---|---|---|
| G01 | instrument identity mapping | PASS | No |
| G02 | `launchTime` / `deliveryTime` / `status` semantics | PASS | No |
| G03 | archive-edge corroboration without event overclaim | PASS | No |
| G04 | historical state-transition and revision reconstructability | FAIL | Yes |
| G05 | settled-event announcement publication time | FAIL | Yes |
| G06 | prospective polling and snapshot determinism | PASS | No |
| G07 | raw lineage and internal evidence retention | FAIL | Yes |

`NO_AUTHORITY` is the single publishable recommendation because historical reconstruction gates fail and the
captured official legal source does not establish permission for internal raw-evidence retention.

## 3. Historical Unknowns That Must Remain Unknown
- Whether Bybit historically exposed inverse completed-delivery instruments through a `status=Settled`
  `instruments-info` filter. The captured official request rejects that parameter.
- Whether Bybit permits the intended internal raw-evidence retention. The single captured official legal
  source returned 403 and no explicit permission clause was captured.
- The exact known-time when `BITUSD` transitioned to `Closed`.
- Any revision/supersession history for past `instruments-info` snapshots.
- A symbol-specific official announcement publication time for the required settled branch from the bounded
  announcement captures.

## 4. Records and State Transition

- `tickets/REF-002.md`: set to `AWAITING_REVIEW`.
- `docs/reviews/REF-002_SOURCE_FEASIBILITY_REPORT.md`: this document.
- `research/ref_002/EVIDENCE_REGISTER.csv`: complete evidence register (28 rows, 20 columns).
- `research/ref_002/decision_matrix.csv`: gate classification with single recommendation.
- `research/ref_002/sources/bybit.md`: Bybit source note for instrument-event feasibility.
- `docs/reviews/REF-002_JR_SOURCE_AUDIT_TASK.md`: COMPLETED - SOURCE AUDIT AND RECORDS.
- `docs/engineering/IMPLEMENTATION_BACKLOG.csv`: REF-002 `AWAITING_REVIEW`.
- `README.md`: REF-002 listed as `AWAITING_REVIEW` with recommendation `NO_AUTHORITY`.
- `docs/handoff/CURRENT_TASK.md`: next actor `Reviewer`, next ticket `NONE`.

## 5. Acceptance Command Evidence

- CSV validator
  - `PASS`
  - `Evidence rows: 28`
- `python3 scripts/check_repo_control.py`
  - `Repo control check: PASS`

## 6. Boundaries

No implementation, schema, migration, ADR, generated dataset, universe, factor, portfolio, or live work is
authorized by this report.
