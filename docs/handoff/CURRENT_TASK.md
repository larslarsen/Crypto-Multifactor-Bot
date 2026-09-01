# CURRENT_TASK

Ticket: CEX-002
State: IN_PROGRESS
Final reviewer: Lead Quantitative Finance Researcher/Engineer
Next required actor: Sr Dev — Codex Sol
Next ticket: NONE
Next ticket authorized: NONE

Review 424 accepts Sol's exact two-path retained-credit correction. The generation-0 loader now
accepts exactly the acquisition module's `checksum_verified` and `retained_credit` states through
one focused helper, while every other authority and lineage check remains unchanged. The targeted
suite passed all 38 cases.

Gate 2 remains `ACCEPTED`; Gate 3 remains `IN_PROGRESS`; no open-interest product is accepted.

Review 426 accepts Hermes commit `85965e9294612123c1b762ad8ba63cfef82a5ed6` and terminal record
425. The sole real run left seven hidden 0GUSDT month partitions without a completion descriptor.
They remain unaccepted, unreferenced evidence.

Read-only diagnosis proves the exact failing `0GUSDT` 2026-04-23 official ZIP has a matching
checksum, 288 unique rows, a complete five-minute day, and shuffled physical CSV order. The
normalizer incorrectly treats physical order as economic time. Gate 2 remains `ACCEPTED`; Gate 3
remains `IN_PROGRESS`; no product is accepted.

Sr Dev — Codex Sol High is authorized only for Review 426's two-path correction: validate and sort
each authenticated contract-day by timestamp while preserving original row ordinal and every raw
value, retain duplicate/conflict rejection, enforce the exact 288-point daily grid bound, add the
focused shuffled-row test, and run the one targeted pytest once. No CLI edit, real-data run,
partial-output mutation, cleanup, retry, runner, integration, Git, network, acquisition, other
product, experiment, model, trading-engine work, or next ticket is authorized.

Governing documents:

- `research/sprint_004/426_CEX002_RECORD425_ACCEPTANCE_AND_DAILY_ROW_ORDER_CORRECTION.md`
- `research/sprint_004/425_CEX002_OPEN_INTEREST_REAL_RUN_RECORD.md`
- `research/sprint_004/424_CEX002_RETAINED_CREDIT_CORRECTION_ACCEPTANCE_AND_REAL_RUN.md`
- `research/sprint_004/423_CEX002_RECORD422_REVIEW_AND_RETAINED_CREDIT_CORRECTION.md`
- `research/sprint_004/422_CEX002_OPEN_INTEREST_INTEGRATION_AND_REAL_RUN_RECORD.md`
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
- `docs/adr/0033-aggregate-prefix-reachability-and-v3-candidate.md`
- `docs/adr/0031-post-plan-revision-authority-and-bounded-zip-validation.md`
- `docs/adr/0030-exact-retained-credit-and-pre-network-plan-retirement.md`
- `tickets/CEX-002.md`
