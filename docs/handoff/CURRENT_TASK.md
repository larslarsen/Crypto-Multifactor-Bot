# CURRENT_TASK

Ticket: BAR-001
State: IN_PROGRESS
Next ticket authorized: NONE
Next required actor: Jr Dev - Hermes

Accepted dependency: BIN-001 at `b881335817e9390011a37afb73b522d985746416`
(REVIEW-0025).
Governing review: docs/reviews/REVIEW-0030_BAR-001_CHANGES_REQUIRED.md

## Authorized work

Complete Jr-side integration against the current production source drop. No production
source changes are authorized. If source defects or mismatches are revealed by tests,
stop and record them for reviewer routing rather than editing source.

## Verified

- Gap between tests and source: full.
- Transform/schema: tests target v3; source is v5.
- Review markers present in source: REVIEW-0028/0029/0030.
- Tests currently pass against the current source.
