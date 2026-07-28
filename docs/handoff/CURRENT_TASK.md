# CURRENT_TASK

Ticket: DATA-008
State: AWAITING_REVIEW
Next required actor: Reviewer
Final reviewer: Sol 5.6 High
Next ticket authorized: NONE

## Summary

Both REVIEW-0247 corrections are implemented, mutation-verified and published.
Source is committed at `d3115b1`; report 36 and the additive manifest both declare
`d3115b1`; dataset `ds_d211884012b1a9fc1e3ed491422f88724b0d107d7d8c9f781b41e4563050d407`
carries 9,027 rows over four additive symbols with 448 raw dependencies and a direct
DATA-006 base dependency. Eighteen identity and reconciliation checks pass.

Additionally, the identity check no longer relies on a hand-maintained four-file
tuple: `resolve_identity_paths()` derives the covered set from the loaded module
closure (36 files), so the publisher, catalog store, output hashing and raw-object
writer are now covered. That closes the recurring false-identity class behind
REVIEW-0243, 0245 and 0247 structurally rather than by patching a list.

Original REVIEW-0247 scope, both done: remove the public
`--skip-identity-check` production bypass and normalize out-of-range earliest-history
timestamp conversion into typed pending failure. Retain all other REVIEW-0246 source
corrections and the additive architecture. Jr Dev owns tests, controls, Git, and final
controlled publication after integration.

## Governing documents

- tickets/DATA-008.md
- docs/reviews/REVIEW-0240_DATA-008_REWORK_AUTHORIZED.md
- docs/reviews/REVIEW-0241_DATA-008_CHANGES_REQUIRED.md
- docs/reviews/REVIEW-0242_DATA-008_CHANGES_REQUIRED.md
- docs/reviews/REVIEW-0243_DATA-008_CHANGES_REQUIRED.md
- docs/reviews/REVIEW-0244_DATA-008_CHANGES_REQUIRED.md
- docs/reviews/REVIEW-0245_DATA-008_CHANGES_REQUIRED.md
- docs/reviews/REVIEW-0246_DATA-008_CHANGES_REQUIRED.md
- docs/reviews/REVIEW-0247_DATA-008_CHANGES_REQUIRED.md

## Authorization

Only the REVIEW-0247 DATA-008 correction pass is authorized. No other ticket or LIVE
work may begin.
