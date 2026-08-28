# CURRENT_TASK

Ticket: CEX-002
State: IN_PROGRESS
Next required actor: Implementation Dev - Codex Spark High - review-332 output/test residual
Final reviewer: Lead Quantitative Finance Researcher/Engineer
Next ticket authorized: NONE

Review 332 accepts Grok's corrected retirement module unchanged at SHA-256
`8e74a6f984ea2ec61a7e2b459e8e8f6c61c199ef5f9233208ac6ea92599bc344`.
The real rejected store and review-330 authority remain untouched.

Spark must edit only the retirement CLI and test. Add `ValueError` to `_emit`'s stdout
write/flush failure catch; broaden the corrupt-SQLite test match to bounded `SQLite`; and add a
retirement flush-failure test mirroring the write-failure test, asserting indeterminate exit,
error text, source absence, and destination presence. Preserve everything else. Do not run
commands/tests or use Git. Return CLI/test hashes and line counts plus test-function count.

Integration, validation, real inspection/retirement, corrected planning, acquisition, later
gates, and next-ticket work remain unauthorized. Next ticket is `NONE`.

Governing documents:

- `tickets/CEX-002.md`
- `research/sprint_004/332_CEX002_RETIREMENT_CORRECTION_ACCEPTANCE_AND_SPARK_RESIDUAL.md`
- `research/sprint_004/330_CEX002_REJECTED_GATE2_RETIREMENT_AUTHORITY.json`
