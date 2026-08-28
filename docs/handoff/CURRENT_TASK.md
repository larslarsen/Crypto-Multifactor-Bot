# CURRENT_TASK

Ticket: CEX-002
State: IN_PROGRESS
Next required actor: Jr Dev - Hermes - review-329 one-test integration and targeted rerun
Final reviewer: Lead Quantitative Finance Researcher/Engineer
Next ticket authorized: NONE

Immediate state: Review 329 accepts Spark's exact fixture-only correction at test SHA-256
`40a75c4e8516f94e9d7528ec036bd7fef964219ac2203768f510364ff30d2624`, 5,676 lines,
and 203 tests. The only diff synchronizes the report-summary retained byte value with the two
existing tampered byte values. Production and CLI remain unchanged; no real Gate-2 data was
touched.

Hermes must preprove the identities and repository state, use explicit Git-write permission,
stage/commit/push only the accepted acquisition test, then run the targeted acquisition pytest
exactly once. Any failure stops without repair or rerun. On success, return the commit and exact
test result; do not create a separate evidence record.

Ruff rerun, production repair, full-suite/repository validation, control, old-store retirement,
planning, acquisition, replay, `verify`, later gates, and next-ticket work remain unauthorized.
Next ticket is `NONE`.

Governing documents:

- `tickets/CEX-002.md`
- `research/sprint_004/329_CEX002_TARGETED_FIXTURE_ACCEPTANCE_AND_INTEGRATION.md`
