# CURRENT_TASK

Ticket: DATA-008
State: READY
Next required actor: Sr Dev - Grok Build
Final reviewer: Sol 5.6 High
Next ticket authorized: NONE

## Summary

REVIEW-0246 confirms the report/manifest now honestly pin executable source `843de6f`,
but the REVIEW-0245 source correction was not implemented. Correct premature
`ALREADY_CURRENT` cursor advancement, malformed ranking/history evidence, contradictory
failed-history reporting, unversioned selection-policy/source queue identity,
mislabelled trade count, and unguarded production `CodeIdentity`. Commit source and
tests before one final controlled publication. Retain the full non-volume measurement
field, mixed-batch safe progress, strict base validation, exact raw lineage, additive
architecture, and full snapshots.

## Governing documents

- tickets/DATA-008.md
- docs/reviews/REVIEW-0240_DATA-008_REWORK_AUTHORIZED.md
- docs/reviews/REVIEW-0241_DATA-008_CHANGES_REQUIRED.md
- docs/reviews/REVIEW-0242_DATA-008_CHANGES_REQUIRED.md
- docs/reviews/REVIEW-0243_DATA-008_CHANGES_REQUIRED.md
- docs/reviews/REVIEW-0244_DATA-008_CHANGES_REQUIRED.md
- docs/reviews/REVIEW-0245_DATA-008_CHANGES_REQUIRED.md
- docs/reviews/REVIEW-0246_DATA-008_CHANGES_REQUIRED.md

## Authorization

Only the REVIEW-0246 DATA-008 correction pass is authorized. No other ticket or LIVE
work may begin.
