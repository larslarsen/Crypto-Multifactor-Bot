# CEX-002 Gate-2 Targeted Test Failure Review

Date: 2026-08-26
Reviewer: Lead Quantitative Finance Researcher/Engineer
Decision: TARGETED TEST REJECTED; ONE BOUNDED GROK CORRECTION AUTHORIZED
Ticket state: IN_PROGRESS
Next required actor: Sr Dev - Grok Build with xhigh reasoning
Next ticket authorized: NONE

## Integrated checkpoint and execution result

Hermes preproved, committed, and pushed exactly the review-304 developer paths in commit
`1b1826d919fbdabed6c10187d7745599f4f94133` (`integrate CEX-002 Gate-2 acquisition
engine`). `HEAD == origin/main`, the three integrated paths are clean, and their identities are:

- `src/cryptofactors/acquisition/binance_usdm_harmonic_acquisition.py`:
  `308b818806be9be3393af19ecf306eb24f88a4884dcf470e664bf8cd2d6a19f2`
- `scripts/research/acquire_binance_usdm_harmonic_release.py`:
  `bb6038559d45bddfb011925ad96eb9552cbe4b71bfd5051375adbdcd3de555a9`
- `tests/acquisition/test_binance_usdm_harmonic_acquisition.py`:
  `e04c47f7485500f1a63d2c505cb5f71df5ff341f3447bb14d34bc4cb27f2c1a8`

Hermes then ran the review-304 targeted command exactly once from
2026-08-26T20:44:31.661903610Z through 2026-08-26T20:44:58.991200575Z. It completed in
27.333 seconds with exit code 1 and eight failures. The first distinct failure was
`test_crash_before_publication_refunds_the_reservation`, raising
`UnsafeStateError: an unsealed fact tail remains`. Hermes stopped without repair, rerun, Ruff,
control, or another command. The reviewer ran no test or acceptance command.

Pytest's recorded current node identities establish these eight failures:

1. `test_crash_before_publication_refunds_the_reservation`
2. `test_a_released_charge_is_retried_as_a_new_generation`
3. `test_retained_raw_source_removal_is_refused`
4. `test_a_seal_link_with_wrong_watermarks_is_refused`
5. `test_published_receipt_without_seal_is_recovered`
6. `test_valid_released_then_retried_generation_is_handled_once`
7. `test_missing_filesystem_receipt_is_republished_from_intent`
8. `test_injected_interruption_records_one_interrupt_attempt`

## Complete static disposition

This result does not justify a chain or recovery redesign. Review 302's central invariant is
correct and remains closed: a new run must not begin over an unfinished run or orphan unsealed
facts, and every recoverable fact tail must be owned by the original unfinished run. The eight
failures have four bounded causes.

### 1. Three charge-recovery fixtures create an impossible orphan tail

Tests 1, 2, and 6 install a plan and then insert charge/transition rows directly without first
creating the run which owned those facts. Their comments call this an interrupted transition,
but every production charge now occurs after `begin_run()`. The resulting orphan tail is exactly
what `_require_runnable_head()` must reject under review 302.

Correct the fixtures, not the invariant. Build a valid bound session, begin one run through the
production state API, leave that run unfinished, and only then create the intended durable
reservation/release facts. Resume must first finalize and seal that original run under its own
identity; the following run may then reconcile the open charge and, where applicable, create the
next immutable generation. Assert the interrupted receipt owns the predecessor-to-current charge
and transition deltas. Retain or add a direct regression proving the same rows without an open
run remain unsafe as an orphan unsealed tail. Do not let a new run absorb them.

### 2. Two publication fixtures delete authenticated history instead of injecting a crash

Tests 5 and 7 complete a valid publication, delete every `run_seal`, and rewind `seal_head` to the
plan receipt. That is destructive authenticated-state mutation, not a process-loss prefix. Since
`run_seal.seq` is autoincrementing, reinsertion also creates a sequence beyond the receipt's
watermark. Production must reject that state.

Replace these setups with the already-supported exact named fault boundaries. Use
`before_run_seal_insert` for a published receipt/locator plus durable intent with no seal. Use
`before_run_receipt_publication` for durable finished intent with no filesystem receipt or
locator. Read the expected run and receipt identities from the durable intent, resume once, and
prove the receipt/locator/seal/head converge. Do not delete seals, rewind the head, reset SQLite
sequence state, or weaken authenticated-history deletion detection.

### 3. Two tests have local assertion/harness defects

Test 4 mutates a predecessor seal watermark. Authentication correctly reaches the dependent run
start snapshot first and reports that it disagrees with its predecessor. Expand the assertion to
accept that precise predecessor diagnostic, or make the existing diagnostic explicitly say
`predecessor watermarks`; do not change the validation order or weaken the rejection.

Test 8 saves `response.iter_bytes`, which is an iterator, but its wrapper executes `inner()` as
if it were callable. That records a `TypeError` transport retry instead of injecting the intended
`FaultInjected` after streamed bytes. Change the wrapper to iterate `inner` directly and retain
the assertions for exactly one statusless `transport` attempt whose fact names the interrupt.
Do not add a production workaround for this test error.

### 4. Retained-source boundary loses its semantic diagnostic

Test 3 removes the retained raw authority file. `_retained_plan_fields()` currently lets the
generic no-follow open error escape before the later retained-credit re-proof can report its
domain. Preserve fail-closed behavior and the original cause, but translate this boundary to an
`AuthorityError` or `UnsafeStateError` which explicitly identifies the retained raw source and
the affected key. Do not fall back to network, mark the row non-retained, or change its plan.

## Grok correction authorization

Keep Grok at xhigh for this bounded architecture-aware correction. Grok may edit only:

- `src/cryptofactors/acquisition/binance_usdm_harmonic_acquisition.py`
- `tests/acquisition/test_binance_usdm_harmonic_acquisition.py`

Preserve the integrated CLI unchanged and preserve every accepted review-304 source mechanism,
especially predecessor-owned deltas, original-run interrupted recovery, orphan-tail refusal,
append-only charge generations, authenticated publication intent and seal history, constant-memory
recovery, exact capacity facts, and coordinator-owned durable error/capacity events. Make all four
groups above in one return. Do not use Git, edit repository records, or execute tests or other
commands. Hermes owns integration and the next targeted test only after reviewer static acceptance.

Stop once with the two exact path hashes, line and test-function counts, and confirmation that no
command ran. Real plan/acquire/verify, network, data, Ruff, full suite, control, evidence edits,
Gate 3, normalization, catalog, NautilusTrader, Harmonic Trader, PAPER/LIVE, and next-ticket work
remain unauthorized.

## Reviewer publication scope

The reviewer may stage, commit, and push exactly this record, `docs/handoff/CURRENT_TASK.md`, and
`tickets/CEX-002.md`. Developer source/test paths, state/data/evidence, and unrelated dirty work
are excluded.
