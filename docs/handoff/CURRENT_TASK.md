# CURRENT_TASK

Ticket: DATA-008
State: READY
Next required actor: Sr Dev - Grok Build
Next ticket authorized: NONE

## Summary

REVIEW-0244 requires one bounded failure-state and cursor correction. Remove the
remaining 24-hour-evidence gate from the 30-day measurement field; distinguish valid
insufficient windows/history from failed or malformed acquisitions; block and retry
unavailable evidence; preserve safe cursor progress in mixed batches; and bind queue
identity to material selection controls without coupling it to processing-day capacity.
Retain the reconciled code identity, closed-bar checks, taxonomy version, strict base
validation, pagination, exact raw lineage, additive architecture, and full snapshots.

## Governing documents

- tickets/DATA-008.md
- docs/reviews/REVIEW-0240_DATA-008_REWORK_AUTHORIZED.md
- docs/reviews/REVIEW-0241_DATA-008_CHANGES_REQUIRED.md
- docs/reviews/REVIEW-0242_DATA-008_CHANGES_REQUIRED.md
- docs/reviews/REVIEW-0243_DATA-008_CHANGES_REQUIRED.md
- docs/reviews/REVIEW-0244_DATA-008_CHANGES_REQUIRED.md

## Authorization

Only the REVIEW-0244 DATA-008 correction pass is authorized. No other ticket or LIVE
work may begin.
