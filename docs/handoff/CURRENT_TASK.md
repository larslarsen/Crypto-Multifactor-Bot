# CURRENT_TASK

Ticket: DATA-008
State: AWAITING_REVIEW
Next required actor: Reviewer
Next ticket authorized: NONE

## Summary

REVIEW-0241 requires one consolidated correction pass. DATA-008 must extend the
accepted DATA-006 panel through a separate, dependency-bound additive dataset; no
`market_bars` publisher or mass instrument-mapping change is authorized. It must rank
additions on actual 30-day evidence, paginate historical klines, persist a multi-day
capacity cursor, complete the terminal selection audit and exclusion taxonomy, and
correct incremental report accounting. Preserve the rewrite's exact raw lineage and
retry-safe full-snapshot controls.

## Governing documents

- tickets/DATA-008.md
- docs/reviews/REVIEW-0240_DATA-008_REWORK_AUTHORIZED.md
- docs/reviews/REVIEW-0241_DATA-008_CHANGES_REQUIRED.md

## Authorization

Only the REVIEW-0241 DATA-008 correction pass is authorized. No other ticket or LIVE
work may begin.
