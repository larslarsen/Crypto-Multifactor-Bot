# CURRENT_TASK

Ticket: CEX-002
State: IN_PROGRESS
Final reviewer: Lead Quantitative Finance Researcher/Engineer
Next required actor: Lead Quantitative Finance Researcher/Engineer
Next ticket: NONE
Next ticket authorized: NONE

Review 417 accepts the corrected three-path `binance_usdm_open_interest_5m` production/test drop
for Hermes integration and one real run. Hermes reproved HEAD and origin/main at 1c565f8 and
reproved all three accepted hashes and line counts. The exact targeted pytest passed all 35 cases.
The exact targeted ruff then failed at tests/ingest/test_binance_usdm_open_interest.py line 222
with F841 because local variable `key` is assigned but unused. Hermes correctly stopped there:
the repository-control check was not run and the real normalization was not launched.

Gate 2 remains `ACCEPTED`. Gate 3 remains `IN_PROGRESS`. The three accepted developer paths
remain unintegrated and unstaged. No real runner/output exists. The next required actor is the
Lead Quantitative Finance Researcher/Engineer. Next ticket remains `NONE`.

Hermes must publish this exact outcome as record 418, update CURRENT_TASK and CEX-002, run
`python3 scripts/check_repo_control.py` as the publication control, stage exactly the record,
CURRENT_TASK, and ticket, commit, push, prove HEAD equals origin/main, and stop. No test or
ruff rerun, no patch, source edit, data, network, acquisition, cleanup, other product, or real
run is authorized. All unrelated dirty paths are preserved.

Governing documents:

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
