# CURRENT_TASK

Ticket: BAR-001
State: IN_PROGRESS
Next ticket authorized: NONE
Next required actor: Jr Dev - Hermes

Accepted dependency: BIN-001 at `b881335817e9390011a37afb73b522d985746416`
(REVIEW-0025).
Governing review: docs/reviews/REVIEW-0033_BAR-001_INTEGRATION_CHANGES_REQUIRED.md

## Authorized work

Complete the Jr integration in REVIEW-0033, retaining REVIEW-0031/0032's full contract.
Jr Dev - Hermes owns focused tests, exact acceptance gates, BAR-001 records, repository
control, Git, commit, and push. No production source changes are authorized. If a test
reveals a source defect, stop and record it for reviewer routing.

## Stop condition

After the complete current suite and every ticket-exact gate pass, update the change
report, commit/push, and stop for final reviewer inspection. Do not open a new ticket.
