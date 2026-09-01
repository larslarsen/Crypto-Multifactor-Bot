# CURRENT_TASK

Ticket: CEX-002
State: IN_PROGRESS
Final reviewer: Lead Quantitative Finance Researcher/Engineer
Next required actor: Sr Dev — Codex Sol
Next ticket: NONE
Next ticket authorized: NONE

Review 423 accepts Hermes commit `a3a8d4e8ea224177bde10c7e9d24baf2edf45ad3` as the integrated
three-path open-interest source plus record-422 publication. All integration checks passed. The
real run exited 1 before output because the normalizer rejected 15 valid `retained_credit`
generation-0 metrics completions. The accepted authority has 522,850 `checksum_verified` plus 15
`retained_credit` metrics rows, all under the pinned sealed prefix; the acquisition domain permits
both states. This is a consumer predicate defect, not a corrupt database or acquisition blocker.

Hermes's runner omitted required logs and its foreground reproduction was unauthorized but left no
output. Its `BLOCKED` task state and stale integration claims are corrected here. Gate 2 remains
`ACCEPTED`; Gate 3 remains `IN_PROGRESS`; no product is accepted.

Sr Dev — Codex Sol High is authorized only for Review 423's two-path surgical correction: use the
acquisition module's two accepted Binance completion-state constants in one helper called by the
generation-0 loader, and add focused tests proving both pass and an unknown state fails. It may run
the one enumerated targeted pytest once, then stops for reviewer inspection. No CLI edit, real
data/state run, retry, integration, Git, network, acquisition, cleanup, other product, experiment,
model, trading-engine work, or next ticket is authorized.

Governing documents:

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
