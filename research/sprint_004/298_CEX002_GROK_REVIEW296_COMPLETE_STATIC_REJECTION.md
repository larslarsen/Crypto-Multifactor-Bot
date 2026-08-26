# CEX-002 Grok Review-296 Complete Static Rejection

Date: 2026-08-25
Reviewer: Lead Quantitative Finance Researcher/Engineer
Decision: REJECTED WITHOUT TESTS; bounded residual correction remains with Grok Build
Ticket state: IN_PROGRESS
Next required actor: Sr Dev - Grok Build on Grok 4.6 High
Next ticket authorized: NONE

## Inspected return

The reviewer performed one complete static inspection of Grok Build's claimed review-296
implementation at:

- `src/cryptofactors/acquisition/binance_usdm_harmonic_acquisition.py`:
  `7a1b78d6572c78568aee30a1b14369810fad95aa20b8ee72e0c146ca377bd28b`
- `scripts/research/acquire_binance_usdm_harmonic_release.py`:
  `bb6038559d45bddfb011925ad96eb9552cbe4b71bfd5051375adbdcd3de555a9`
  (unchanged)
- `tests/acquisition/test_binance_usdm_harmonic_acquisition.py`:
  `5bbc14acfa00437dbc03da734402a95cf640b100d8c5a350de6a11633245af2f`

The files contain 9,272, 151, and 3,741 lines. The test source has 142 test functions.
No developer command result was supplied. The reviewer ran no test or acceptance command
because the source and direct-regression contract remains incomplete.

## Decision

Reject the return without a test cycle, but retain Grok for one bounded correction because
this is a substantial implementation rather than another token fragment. Preserve its
out-of-capability refusal and bound override roots, removed code-path prechecks, forwarded
authority roots, rollback-journal ownership, post-bind cleanup ownership, run IDs and exact
receipt key sets, receipt-recovery skeleton, exact charge generations and validator,
statusless transport class, acquisition-owned retained proof, exact inventory-set check,
authority/ledger terminal records, deterministic bound telemetry, and 18 added regressions.

The following residuals are blocking. They are implementation defects within review 296,
not a new architecture or economic contract.

## Complete residual correction

### 1. Manifest and receipt-root operations still escape or misidentify the capability

`iter_plan_objects()` calls `iter_selected_binance()` without `roots`. That function calls
the qualification module's `iter_manifest_detail()`, which validates and opens the accepted
gzip through pathnames. This is still an authority read outside the retained session
capability. Implement an acquisition-owned descriptor-streaming manifest proof/iterator or
an equivalently exact bound adapter. Do not alter the accepted detail format or identity.

The new authority-swap test swaps at `before_raw_publication`, after authority and manifest
reads, so it does not prove this path. Inject the swap at the actual manifest open/read.

`AcquisitionState._receipt_dirs()` derives fixed `gate2/run_receipts` and
`gate2/plan_receipts` paths from the state parent rather than using the configured, bound
`AcquisitionPaths` receipt roots. Recovery therefore cannot find legitimate operator-
overridden receipt locations. Give state the exact bound receipt roots and test an override.

### 2. Run receipts are key-bounded but not exact authenticated run records

`_validate_receipt_document()` now proves the key set, authority, code, run ID, run times,
stop reason, and network-call total. It does not prove `attempt_delta`,
`completion_delta`, `gap_delta`, `byte_delta`, `attempts`, `error_count`, `network_sample`,
pre/post capacity, `capacity_blocked`, open charges, counts, or `semantic_state_digest`
against durable state and predecessor watermarks. Historical receipts inherit the same
gap. Persist or deterministically derive every retained field and compare it exactly; omit
no accepted field from authentication.

There are still no fault points at the run-receipt publication, `run_seal` insertion, or
head-CAS boundaries. The new recovery tests manually delete/reset valid state after the
fact, so they do not prove the executable crash transitions. Add the exact before/after
fault points and test each boundary, including malformed, missing, and ambiguous candidates.
Make recovery enumeration bounded; `_iter_bound_receipts()` currently materializes every
directory name with `os.listdir()`.

### 3. Attempt and charge paths can still seal contradictory state

On an allowed 200/404 response, a `close_response()` failure records `RETRY_TRANSPORT` with
that response status. `DOMAIN_CHECKS` explicitly rejects transport attempts with 200 or
404. A streamed `FaultInjected` records `RETRY_TRANSIENT` with status 200, while the domain
rejects every non-null transient status below 500. The current run does not reauthenticate
domains before writing its receipt, so either invalid fact can be sealed and only fail on a
later open. Use exact classifications/status domains for header, read, validator,
interruption, and close failures; authenticate the complete state before sealing. Add each
direct call regression and prove exactly one attempt with the original bounded cause.

Use `validate_charge_against_plan()` on the normal reserve/publish/complete path as review
296 requires, not only recovery, existing settlement, and terminal verification. Also fix
or remove `iter_open_charges()`: it still selects every generation row and resolves each to
the newest identity generation, recreating the generation alias fixed in the batch helper.
The added released/retried test merely inserts a generation with no transition and expects
failure; add a valid released-then-retried recovery proving each generation is handled once.

### 4. Initial retained plan proof remains conditional and under-tested

`_retained_plan_fields()` records the raw digest/bytes/path without opening the raw source,
and it opens the sidecar only when the progress record lacks a positive sidecar byte count.
Consequently `run_plan()` can install immutable retained facts that were not proved from
the bound raw and sidecar descriptors. Re-prove both sources unconditionally while forming
the plan and bind the exact bytes, digest/revision, retrieval, device/inode, and source
paths used by adoption/resume/verify.

Keep the corrected direct inventory-validator test. Add the remaining independent
missing/replaced/copied raw, changed sidecar, missing/altered inode/device, label,
count/byte/membership, and five-cost-key regressions required by review 296.

### 5. Terminal reconstruction does not reproduce either authenticated digest

The manifest emits completions and sidecars without their sequence numbers and in
provider/identity order, while `_prefix_digest_unlocked()` hashes both in sequence order
with sequence numbers. `prefix_digest_from_terminal_records()` therefore hashes `seq=None`
for completions and cannot equal the prefix. It also consumes every seal link although the
head prefix excludes the current non-cyclic link, ignores head watermarks, accepts a
universe-sized `Sequence`, and never reconstructs the terminal semantic digest's live-ledger
layer.

Emit every exact ordered field needed for both digests and implement a bounded streaming
reconstructor governed by the emitted head watermarks. The test must reconstruct the head
prefix and terminal semantic digest from manifest bytes alone and compare both identities.
The current test loads the whole manifest and compares selected records back to mutable
SQLite; it is not the required independent proof.

## Grok correction authorization

Grok Build may edit only the same three developer paths listed above. Implement every
residual and its direct regression together. Preserve all accepted architecture, authority,
economic scope, counts, bytes, capacity, and the useful changes named in this review. Use no
Git and edit no other path.

No test may run until the complete residual source and regression matrix is present. The
targeted allowance does not reset: across reviews 295-298, at most three runs of the exact
review-291 pytest command are permitted, counting any unreported run. Run no Ruff, control,
qualification, sizing, capacity, real plan/acquire/verify, network, Git, or other command.

Stop once with final hashes, line and test-function counts, exact three-path scope, every
authorized command/result with cumulative run number, and the original exception type and
cause for any failure. Hermes retains integration, broader tests/acceptance commands,
evidence, and developer-source Git. No real plan, data, Gate 3, normalization, catalog,
NautilusTrader, Harmonic Trader, PAPER/LIVE, or next-ticket work is authorized.

## Reviewer publication scope

The reviewer may stage, commit, and push exactly this review,
`docs/handoff/CURRENT_TASK.md`, and `tickets/CEX-002.md`. Developer source/test paths,
state/data/evidence, and unrelated dirty work are excluded.
