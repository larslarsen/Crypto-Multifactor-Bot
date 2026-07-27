# CURRENT_TASK

Ticket: DATA-008
State: AWAITING_REVIEW
Next required actor: Reviewer
Next ticket authorized: NONE

## Summary

REVIEW-0243 requires a bounded final correction pass. Republish with the real source
commit, separate persistent queue position from the daily capacity counter, prove the
final 30-day bar is closed, bump the changed taxonomy version, strictly reconcile the
pinned base files, and remove stale prefilter controls. No `market_bars` publisher or
mass instrument-mapping change is authorized. Preserve full-universe ranking,
pagination, exact raw lineage, snapshot-derived union accounting, and retry-safe
publication.

## Governing documents

- tickets/DATA-008.md
- docs/reviews/REVIEW-0240_DATA-008_REWORK_AUTHORIZED.md
- docs/reviews/REVIEW-0241_DATA-008_CHANGES_REQUIRED.md
- docs/reviews/REVIEW-0242_DATA-008_CHANGES_REQUIRED.md
- docs/reviews/REVIEW-0243_DATA-008_CHANGES_REQUIRED.md

## Authorization

Only the REVIEW-0243 DATA-008 correction pass is authorized. No other ticket or LIVE
work may begin.
