# CURRENT_TASK

Ticket: CEX-002
State: IN_PROGRESS
Final reviewer: Lead Quantitative Finance Researcher/Engineer
Next required actor: Jr Dev — Hermes
Next ticket: NONE
Next ticket authorized: NONE

Review 421 accepts Sol's function-scoped correction. The required test-local `key` is restored,
the unused neighboring copy is removed, and Sol's sole targeted ruff command passed. The accepted
production source and CLI remain unchanged; the accepted test is now 439 lines at SHA-256
`4c6d796ee1e7ec8e1b5b0b2ffe1ac1ad581aee6777e661401e086cc02ac9f8b5`.

Gate 2 remains `ACCEPTED`. Gate 3 remains `IN_PROGRESS`. The three developer paths remain
unintegrated and unstaged.

Jr Dev — Hermes is authorized under Review 421 to reprove the three accepted paths, run the three
ordered integration checks, verify output absence and at least 100 GiB available, then launch and
poll exactly one durable real open-interest normalization runner. A live runner survives harness
exit and is continued only by exact identity. Every terminal outcome is published as record 422
with the three developer paths and exact control records. No patch, duplicate run, acquisition,
network, cleanup, other product, experiment, model, trading-engine work, or next ticket is
authorized.

Governing documents:

- `research/sprint_004/421_CEX002_LINT_CORRECTION_ACCEPTANCE_AND_REAL_RUN_REAUTHORIZATION.md`
- `research/sprint_004/420_CEX002_REVIEW419_LINT_STOP_AND_FUNCTION_SCOPED_CORRECTION.md`
- `research/sprint_004/419_CEX002_RECORD418_ACCEPTANCE_AND_ONE_LINE_LINT_CORRECTION.md`
- `research/sprint_004/418_CEX002_OPEN_INTEREST_INTEGRATION_LINT_STOP_RECORD.md`
- `research/sprint_004/417_CEX002_OPEN_INTEREST_SOURCE_ACCEPTANCE_INTEGRATION_AND_REAL_RUN.md`
- `research/sprint_004/416_CEX002_OPEN_INTEREST_SOURCE_STATIC_REJECTION_AND_CORRECTION.md`
- `research/sprint_004/415_CEX002_RECORD414_ACCEPTANCE_GATE2_AND_OPEN_INTEREST_AUTHORIZATION.md`
- `research/sprint_004/414_CEX002_DIRECT_RECOVERY_TERMINAL_BLOCKER_RECORD.md`
- `research/sprint_004/413_CEX002_RECORD412_ACCEPTANCE_AND_DIRECT_RECOVERY_AUTHORIZATION.md`
- `docs/adr/0034-direct-pending-raw-recovery.md`
- `research/sprint_004/412_CEX002_DURABLE_V3_CONTINUATION_RECORD.md`
- `docs/adr/0033-aggregate-prefix-reachability-and-v3-candidate.md`
- `docs/adr/0031-post-plan-revision-authority-and-bounded-zip-validation.md`
- `research/sprint_004/354_CEX002_GATE2_END_OF_PLAN_REVIEW_AND_REVISION_ARCHITECTURE.md`
- `tickets/CEX-002.md`
