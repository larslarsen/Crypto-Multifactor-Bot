# CURRENT_TASK

Ticket: CEX-002
State: IN_PROGRESS
Next required actor: Jr Dev - Hermes - review-335 exact integration and focused validation
Final reviewer: Lead Quantitative Finance Researcher/Engineer
Next ticket authorized: NONE

Review 335 accepts Grok's exact retirement module/test descriptor-continuity correction. Hermes
must integrate and push only those two paths, run focused Ruff once, then run the targeted
synthetic retirement-tool suite once on Ruff success. Stop on the first failure without repair
or rerun; on two passes return the integration commit and exact command results without an
evidence record.

Do not invoke the retirement CLI or inspect or mutate the real rejected store. Real retirement,
corrected planning, acquisition, later gates, and next-ticket work remain unauthorized. Next
ticket is `NONE`.

Governing documents:

- `tickets/CEX-002.md`
- `research/sprint_004/335_CEX002_RETIREMENT_DESCRIPTOR_CORRECTION_ACCEPTANCE_AND_VALIDATION.md`
- `research/sprint_004/330_CEX002_REJECTED_GATE2_RETIREMENT_AUTHORITY.json`
