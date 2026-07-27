# CURRENT_TASK

Ticket: DATA-008
State: AWAITING_REVIEW
Next required actor: Reviewer
Final reviewer: Sol 5.6 High
Next ticket authorized: NONE

## Summary

REVIEW-0245 requires one bounded validation, cursor, and code-identity correction.
Republish from the final clean source commit; persist `ALREADY_CURRENT` only after prior
coverage reconciles; fail closed on malformed ranking/history timestamps; keep failed
history out of deferred evidence; version selection-policy/source identity in the
queue; and report actual trades rather than bar count. Retain the full non-volume
measurement field, typed HTTP failure blocking, mixed-batch safe progress, closed-bar
checks, strict base validation, exact raw lineage, additive architecture, and full
snapshots.

## Governing documents

- tickets/DATA-008.md
- docs/reviews/REVIEW-0240_DATA-008_REWORK_AUTHORIZED.md
- docs/reviews/REVIEW-0241_DATA-008_CHANGES_REQUIRED.md
- docs/reviews/REVIEW-0242_DATA-008_CHANGES_REQUIRED.md
- docs/reviews/REVIEW-0243_DATA-008_CHANGES_REQUIRED.md
- docs/reviews/REVIEW-0244_DATA-008_CHANGES_REQUIRED.md
- docs/reviews/REVIEW-0245_DATA-008_CHANGES_REQUIRED.md

## Authorization

Only the REVIEW-0245 DATA-008 correction pass is authorized. No other ticket or LIVE
work may begin.
