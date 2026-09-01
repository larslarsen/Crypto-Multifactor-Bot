# CURRENT_TASK

Ticket: CEX-002
State: IN_PROGRESS
Final reviewer: Lead Quantitative Finance Researcher/Engineer
Next required actor: Lead Quantitative Finance Researcher/Engineer
Next ticket: NONE
Next ticket authorized: NONE

Review 424 accepts Sol's exact two-path retained-credit correction. The generation-0 loader now
accepts exactly the acquisition module's `checksum_verified` and `retained_credit` states through
one focused helper, while every other authority and lineage check remains unchanged. The targeted
suite passed all 38 cases.

Gate 2 remains `ACCEPTED`; Gate 3 remains `IN_PROGRESS`; no open-interest product is accepted.

Jr Dev — Hermes launched exactly one logged detached real normalization runner under Review 424 at
`/tmp/cex002_oi_424_bWtKo4`. The runner terminated with exit 1 at 2026-09-01T19:03:56Z after ~4 min
40 sec, raising `OpenInterestNormalizationError: metrics timestamps are not strictly increasing` at
`src/cryptofactors/ingest/binance_usdm_open_interest.py:1216`. The hidden output
`data/.cex002_open_interest_5m` contains partial, unreferenced artifacts (one symbol, seven months,
no completion descriptor). The prior status poll (session `20260901_120304_ff3146`) raced terminal
completion, reporting the runner live at 19:03:58Z against the recorded end UTC of 19:03:56Z.

Hermes publishes terminal record 425 and returns both control files to the reviewer. No source/test
patch, cleanup, retry, reproduction, acquisition, network, other product, experiment, model,
trading-engine work, or next ticket is authorized.

Governing documents:

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
