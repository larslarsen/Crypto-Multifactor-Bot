# CURRENT_TASK

Ticket: CEX-002
State: IN_PROGRESS
Final reviewer: Lead Quantitative Finance Researcher/Engineer
Next required actor: Sr Dev — Codex Sol
Next ticket: NONE
Next ticket authorized: NONE

Review 420 accepts Sol's Review-419 attempt as a safe lint stop. The deletion instruction was
ambiguous because the same assignment occurred in two neighboring functions: the used occurrence
was removed, leaving F821 at line 213 and the original F841 at line 221. No real run, runner,
output, integration, or other source mutation occurred.

Gate 2 remains `ACCEPTED`. Gate 3 remains `IN_PROGRESS`. The three developer paths remain
unintegrated and unstaged.

Sr Dev — Codex Sol High is authorized only for Review 420's two function-scoped test edits: restore
`key` inside `test_unsafe_zip_member_paths_are_rejected` immediately before `payload`, and remove
the unused `key` inside `test_symlink_and_multi_member_zips_are_rejected`. It may then run the one
enumerated targeted ruff command once and stop for reviewer inspection. No other edit, pytest,
real data/state, runner, integration, Git, network, acquisition, cleanup, other product, or next
ticket is authorized.

Governing documents:

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
