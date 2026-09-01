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

Review 427 accepts Sol's exact two-path daily-order correction. Every authenticated contract-day
is validated, bounded to the 288 possible five-minute grid points, then stable-sorted by timestamp
while preserving original row ordinal and every raw value. Duplicate/conflict and all downstream
economic checks remain. The focused suite passed all 39 cases.

The eight existing 0GUSDT month partitions and lineage files remain hidden, unaccepted evidence
without a completion descriptor. They are content-addressed and will be verified/reused without
cleanup. Gate 2 remains `ACCEPTED`; Gate 3 remains `IN_PROGRESS`; no product is accepted.

Jr Dev — Hermes executed the Review-432 terminal evidence workflow. The sole runner
`/tmp/cex002_oi_432_f07dUK` exited 1 at 2026-09-01T20:15:03Z with
`UnsafeStateError: a receipt intent names a different run receipt directory` at
`src/cryptofactors/acquisition/binance_usdm_harmonic_acquisition.py:6682` inside
`_authenticate_run_publication`, called from `_validate_receipt_document`,
`_authenticate_prefix`, `_require_fixed_generation0_terminal`,
`load_generation0_sources`, and `normalize_from_authorities`. The launch harness
reported live at about 31 seconds; the process terminated at 42 seconds. The hidden
root is unchanged at eight Parquets plus eight lineages, empty staging, and no
completion descriptor. Record 433 is published. Both actor fields return to the
reviewer. No source/test/CLI patch, cleanup, reproduction, retry, or next ticket is
authorized.

Review 434 accepts those terminal facts and rejects the blocker diagnosis. The accepted database
stores repository-relative `data/cex002_qualify/gate2/run_receipts`; Review 432 changed the state
argument to an absolute path, causing the authenticator to derive a different absolute directory.
The earlier relative command passed this check and published the existing months. No database,
receipt, source, data, or acquisition repair is needed.

Hermes executed the Review-434 terminal evidence workflow. The sole runner
`/tmp/cex002_oi_434_DmfuB0` exited 1 at 2026-09-01T20:31:10Z (6 minutes 16 seconds after start)
with `OpenInterestNormalizationError: metrics create_time is off the five-minute grid` at
`src/cryptofactors/ingest/binance_usdm_open_interest.py:801` inside `_timestamp`, called from
`_row_values` line 830. The normalizer passed the generation-0 receipt-authentication stage that
failed in Review 432, loaded generation-0 sources, descended the open-interest tree into per-row
timestamp validation, and reached the five-minute-grid check. The path-identity resume is
successful: the accepted relative arguments authenticate and run deep into the normalizer. This is
a bounded normalizer defect in per-row five-minute-grid validation, not an authority or launch
defect.

The lead reviewer interrupted only the still-waiting Hermes harness after the runner was already
terminal; no live runner was signaled. No retry or cleanup occurred.

The hidden root now contains 181 Parquets plus 181 matching lineages, empty staging, and no
completion descriptor. This is 173 new pairs beyond the prior eight 0GUSDT months. The last
published partition is `1000FLOKIUSDT/2024-03`. The prior eight 0GUSDT months are unchanged. No
mutation occurred.

Record 435 is published at commit `9db8583ed39a0a4bf96fe4eb56cbbf58830b265c`. Both actor fields
return to the Lead Quantitative Finance Researcher/Engineer. Next ticket remains `NONE`. Gate 2
remains accepted; CEX-002 and Gate 3 remain `IN_PROGRESS`. No source/test/CLI patch, retry, or
reproduction is authorized.

Governing documents:

- `research/sprint_004/435_CEX002_OPEN_INTEREST_RESUME_RECORD.md`
- `research/sprint_004/434_CEX002_RECORD433_ACCEPTANCE_AND_PATH_IDENTITY_RESUME.md`
- `research/sprint_004/433_CEX002_OPEN_INTEREST_RESUME_RECORD.md`
- `research/sprint_004/432_CEX002_RECORD431_ACCEPTANCE_AND_ABSOLUTE_PATH_RESUME.md`
- `research/sprint_004/431_CEX002_OPEN_INTEREST_RESUME_RECORD.md`

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

Review 430 accepts Sol's exact two-path correction at source SHA-256 `bf6c5c44…` (1,493 lines)
and test SHA-256 `3cd77872…` (576 lines). Every physical row remains fully validated. Only one
adjacent-next-midnight spillover may be excluded when owned rows remain; it is omitted from product
economics, recorded by exact source/ordinal lineage, and counted in final completion. The focused
suite passed all 42 cases. Unaffected lineages omit the new field and remain byte-identical.

Hermes is authorized to reprove and integrate the two accepted paths, run the three ordered
checks, recompute Review 430's exact capacity equation, then launch one durable detached resume
against the same hidden root. There is no acquisition or redownload. Every terminal outcome is
record 431; a live runner is only monitored by its exact identity. No patch, cleanup, duplicate
run, other product, experiment, model, trading-engine work, or next ticket is authorized.

Record 431 states the exact failed Review-430 launch outcome. Hermes integrated and pushed the
accepted source/test correction at commit `a243932d266b9a0ba88266af705febe9eaf91359`, but then
created two wrapper attempts instead of one. Both exited 127 before Python executed because the
relative `.venv/bin/python` path was resolved from the wrong working directory; both Python start
ticks are empty. The reviewer interrupted the harness to prevent a third attempt. The hidden root
is unchanged at eight Parquets plus eight lineages, empty staging, and no completion descriptor.
Both actor fields return to the reviewer. No retry or launch is authorized.

Review 432 accepts record 431 and the integrated correction. Both failed wrappers used a relative
Python path from the wrong working directory and exited before Python ran; this is an operational
launch defect, not a normalizer, data, or acquisition defect. The untracked repository wrapper is
not authority and is forbidden.

Hermes is authorized for one absolute-path detached resume using Review 432's fixed `/tmp`
supervisor contract. It performs no source edit or repeated test and does not download anything.
The launch harness must return immediately with one exact runner identity; any launch uncertainty
is terminal and cannot be retried. Later continuations only monitor that runner and publish record
433 at terminal. No cleanup, duplicate run, other product, experiment, model, trading-engine work,
or next ticket is authorized.

Governing documents:

- `research/sprint_004/432_CEX002_RECORD431_ACCEPTANCE_AND_ABSOLUTE_PATH_RESUME.md`
- `research/sprint_004/431_CEX002_OPEN_INTEREST_RESUME_RECORD.md`
- `research/sprint_004/430_CEX002_MIDNIGHT_SPILLOVER_CORRECTION_ACCEPTANCE_AND_RESUME.md`
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
