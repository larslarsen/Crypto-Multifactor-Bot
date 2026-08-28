# CURRENT_TASK

Ticket: CEX-002
State: IN_PROGRESS
Next required actor: Jr Dev - Hermes - review-338 corrected network-free plan and record 339
Final reviewer: Lead Quantitative Finance Researcher/Engineer
Next ticket authorized: NONE

Review 338 accepts record 337 and the exact ADR-0030 preservation retirement. Hermes must run
the corrected network-free `plan` once, then publish record 339. Only an exit-0 plan permits the
specified read-only receipt/SQLite/inventory reconciliation. Do not rerun planning or invoke
`verify`.

Acquisition, network access, later gates, and next-ticket work remain unauthorized. Next ticket
is `NONE`.

Governing documents:

- `tickets/CEX-002.md`
- `research/sprint_004/338_CEX002_RETIREMENT_ACCEPTANCE_AND_CORRECTED_PLAN_AUTHORIZATION.md`
- `research/sprint_004/337_CEX002_REJECTED_GATE2_RETIREMENT_EXECUTION.md`
