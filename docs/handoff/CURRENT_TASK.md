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

Review 427 accepts Sol's exact two-path daily-order correction. Every authenticated contract-day
is validated, bounded to the 288 possible five-minute grid points, then stable-sorted by timestamp
while preserving original row ordinal and every raw value. Duplicate/conflict and all downstream
economic checks remain. The focused suite passed all 39 cases.

The eight existing 0GUSDT month partitions and lineage files remain hidden, unaccepted evidence
without a completion descriptor. They are content-addressed and will be verified/reused without
cleanup. Gate 2 remains `ACCEPTED`; Gate 3 remains `IN_PROGRESS`; no product is accepted.

Jr Dev — Hermes executed the Review-427 terminal evidence workflow. The sole runner
`/tmp/cex002_oi_427_yZ3DpH` exited 1 at 2026-09-01T19:35:40Z with
`OpenInterestNormalizationError: metrics row lies outside its source contract-day` at
`src/cryptofactors/ingest/binance_usdm_open_interest.py:831` inside `_row_values`, called from
`_normalize_open_interest_tree` line 1209. The hidden root now holds eight 0GUSDT Parquets plus
eight lineage JSONs (2025-09 through 2026-04), empty `.staging`, and no completion descriptor.
Record 428 is published. Both actor fields return to the reviewer. No source/test/CLI patch,
cleanup, reproduction, retry, or next ticket is authorized.

Review 429 accepts record 428 and identifies the exact first failing source row. The accepted
generation-0 0GUSDT metrics object for 2026-05-03 contains 287 owned points from 00:05 through
23:55 plus one next-day 00:00 spillover. The separate accepted 2026-05-04 object owns a different
00:00 value. This is a bounded normalizer defect, not an acquisition blocker: Gate 2 remains
accepted and all raw data remains preserved.

Sr Dev — Codex Sol is authorized only for Review 429's two-path correction. The filename day
remains authority; exactly one fully validated adjacent-next-midnight spillover may be excluded
from product rows and recorded durably by source hash and original ordinal. The missing owned-day
grid point remains an explicit typed gap, and the next-day-owned value wins without imputation or
rewriting. Sol may run one targeted pytest command, then stops for reviewer inspection. No real
run, data mutation, integration, cleanup, retry, acquisition, other product, model, experiment,
trading-engine work, or next ticket is authorized.

Governing documents:

- `research/sprint_004/429_CEX002_RECORD428_ACCEPTANCE_AND_MIDNIGHT_SPILLOVER_CORRECTION.md`
- `research/sprint_004/428_CEX002_OPEN_INTEREST_RESUME_RECORD.md`
- `research/sprint_004/427_CEX002_DAILY_ORDER_CORRECTION_ACCEPTANCE_AND_RESUME.md`
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
