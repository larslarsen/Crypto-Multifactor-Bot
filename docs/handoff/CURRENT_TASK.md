# CURRENT_TASK

Ticket: FUND-002
State: IN_PROGRESS
Next ticket authorized: NONE
Next required actor: Jr Dev - Hermes

Accepted dependency: FUND-001 readiness under REVIEW-0093. FX-002 remains accepted with no viable
primary source.
Governing documents:
- tickets/FUND-002.md
- docs/architecture/02_DATA_SOURCE_PLAN.md
- research/sprint_003/sources/binance.md
- docs/reviews/FUND-001_READINESS_REPORT.md
- docs/reviews/REVIEW-0093_FUND-001_ACCEPTED_FUND-002_AUTHORIZED.md
- docs/reviews/FUND-002_JR_SOURCE_SEMANTICS_AUDIT_TASK.md

## Authorized work

FUND-002 bounded source-semantics audit only under
`docs/reviews/FUND-002_JR_SOURCE_SEMANTICS_AUDIT_TASK.md`. No implementation, schema, migration, ADR,
realized-cashflow, factor, portfolio, or USD-conversion work is authorized.

## Stop condition

After publishing FUND-002 evidence records, set FUND-002 to `AWAITING_REVIEW`, name Reviewer as next
actor, retain `Next ticket authorized: NONE`, and stop. Do not begin another ticket.
