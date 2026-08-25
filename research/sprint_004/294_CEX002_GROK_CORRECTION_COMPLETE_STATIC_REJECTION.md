# CEX-002 Grok Correction Complete Static Rejection

Date: 2026-08-25
Reviewer: Lead Quantitative Finance Researcher/Engineer
Decision: REJECTED ON COMPLETE STATIC REVIEW; one complete correction retained by Grok
Ticket state: IN_PROGRESS
Next required actor: Sr Dev - Grok Build on Grok 4.6 High
Next ticket authorized: NONE

## Inspected correction

The reviewer inspected Grok Build's completed review-293 correction once at:

- `src/cryptofactors/acquisition/binance_usdm_harmonic_acquisition.py`:
  `76476e7e567686b45a7fd3560bade34ad5905fabe7912e80b5c490122375db76`
- `scripts/research/acquire_binance_usdm_harmonic_release.py`:
  `bb6038559d45bddfb011925ad96eb9552cbe4b71bfd5051375adbdcd3de555a9`
  (unchanged)
- `tests/acquisition/test_binance_usdm_harmonic_acquisition.py`:
  `a65f41baee88ea669379351275d6ed3e67f4f5d73655f6c63abfcc9dc3ea9341`

The source, CLI, and test file contain 7,323, 151, and 2,680 lines. The test source has
95 test functions. No developer command result was supplied and the reviewer ran no test
or acceptance command.

## Decision

Reject the correction as one unit without test execution. The drop adds useful foundations:
retained repository/store descriptors, a stable SQLite state-parent URI, exact WAL-mode and
extra-schema checks, insertion sequences for the mutable fact classes, streamed terminal
sections with an exact row equation and private-file cleanup, response validators inside the
attempt boundary, raw retained-source inode proof, duplicate inventory-native refusal, and
the requested ZIP expansion check. Preserve those corrections.

The implementation does not satisfy review 293 as a complete contract. Most operations do
not use the retained roots; the alleged immutable lineage omits a trusted run field and
mutates sealed charge facts; first-run receipt recovery searches the wrong directory; close
failure creates two attempts for one call; normal Coinalyze completion changes its immutable
retrieval fact; retained sidecar-source authority is still not re-proved; terminal verify can
publish an unsealed tail; and the required direct regression matrix is largely absent.

This is one complete static decision. Correct every finding below together before any test
command. Do not return another local subset.

## Blocking findings and exact correction

### 1. Retained roots and SQLite sidecars are not the operational roots

`BoundRoots` is passed to `AcquisitionState` and its store descriptor is used for the initial
real-filesystem capacity check. Authority/code reads, plan and run receipts, response
temporaries, retained sources, content probes/publication, receipt lookup, and terminal
publication still call the pathname-root `open_regular_file()`, `open_parent_dir()`, or
`open_dir_chain()` helpers. `run_acquire()` constructs `CapacityGuard` and all worker calls
with the original unbound filesystem; `verify_state()` likewise publishes through it.
`_cleanup_partials()` runs before session binding and before the writer lock, so it can act on
a swapped pathname or another invocation's live private file.

Thread one session root capability through authority loading, capacity, state, temporary,
content, retained-source, receipt, cleanup, and terminal operations. Every descendant open,
link, rename, unlink, stat, and `statvfs` must be relative to the retained repository/store
descriptors. Acquire and prove the writer state before invocation cleanup. A full-session
ancestor rename/swap must continue against the original descriptors; testing `BoundRoots`
alone is not sufficient.

`AcquisitionState.open()` checks WAL/SHM only after `PRAGMA journal_mode=WAL`, so SQLite may
already have followed a pre-existing `-wal` or `-shm` symlink. The separately held database
fd is not compared to the leaf SQLite actually opened. Prove any pre-existing database,
WAL, and SHM leaves no-follow before SQLite can use them; re-prove their regular identity
after setup, retain the relevant descriptors through close, and fail closed on replacement,
journal fallback, or any setup/close error. Add the complete review-293 state/WAL/SHM
symlink, contention, setup-failure, nested-close, and full-session ancestor-swap tests.

### 2. The receipt lineage is not an immutable authenticated chain

`iter_run_facts()` omits `run_metadata.receipt_sha256`. That avoids a receipt self-hash
cycle, but it leaves a trusted field outside the sealed prefix while
`_recover_published_receipt_head()` trusts that exact field to select the next receipt.
Split the immutable run fact from its receipt-link/seal fact, or use another non-cyclic
append-only representation, so every accepted run field and receipt identity is
authenticated before use. Do not solve the cycle by silently omitting a trusted column.

The head check rehashes only the head and one predecessor. It neither walks the chain to the
installed plan receipt nor validates canonical receipt bytes, receipt schema/authority,
exact documented high-watermarks, watermark domains, or monotone predecessor-to-successor
bounds. A watermark larger than the actual stream can hash the same rows. The mutable head
can therefore describe facts not authenticated by its receipt. Validate canonical bytes and
all receipt fields, compare the head pointer exactly with the receipt, require non-negative
in-range stable watermarks, and authenticate the complete chain to the installed plan
receipt. Advance the pointer with a predecessor compare-and-swap.

Publish-before-head recovery is also incomplete. When the plan receipt is still the head,
the code looks for the first run receipt in `plan_receipts/`, not `run_receipts/`. A missing
or malformed recorded candidate is silently ignored. Locate it through the bound accepted
receipt roots, require its exact recorded identity, and fail closed rather than accepting an
unsealed tail. Reconcile and provider-validate every legitimate crash-tail fact before any
new network scheduling and before extending the chain.

`coinalyze_charge.status` is mutated from reserved to published to settled even though the
whole descriptor is included in earlier prefixes. A later transition therefore rewrites a
previously sealed fact. `release_charge()` deletes the descriptor and its transitions,
destroying stable sequence history. Make descriptors and transitions append-only, derive
current state from the immutable transition stream, and represent an unpublished refund as
an authenticated append-only transition rather than deletion. The same rule applies to run
facts and every other sealed stream.

### 3. Accepted domains and canonical facts remain under-specified

The schema-object equality is now exact, but `DOMAIN_CHECKS` still validates only fragments.
It does not prove canonical JSON for plan, authority, attempt, completion, charge, transition,
gap, and run documents; canonical UTC timestamps and ordering; exact provider/kind/outcome
combinations; attempt class/status relationships; non-negative integer/status/point domains;
exact charge transition order and descriptor state; exact run completion/receipt fields; or
seal predecessor and watermark domains. It also permits provider/kind combinations that are
individually known but mutually invalid.

Authenticate every accepted field and cross-row relationship before scheduling network work
or publishing terminal evidence. Add independent mutation/deletion tests for authority,
plan, gaps, completions, sidecars, ledger, charge descriptors, transitions, attempts, runs,
seal/head, receipt bytes, predecessor links, and unsealed tails. Each test must start from an
independent valid fixture and exercise resume or verify refusal, not merely compare two
self-computed digests.

### 4. One actual call still does not produce one exact attempt

On an allowed response close failure, the inner `finally` records a transient attempt and
re-raises; the outer exception handler records the same physical call again. The invocation
then violates its own call/attempt equality. On a disallowed-status close failure, the raw
exception escapes without the retry behavior implied by its transient classification.
`HttpxStreamTransport._close()` swallows explicit close errors, and a transport-raised
`AcquisitionError` is classified terminal without distinguishing retryable transport/read
failure from terminal validation. `_diagnostic()` truncates characters, not encoded bytes.

Give one owner responsibility for recording each call exactly once after response close and
validation. Preserve one bounded byte-counted, secret-redacted cause; type retryable
transport/read/close failures separately from terminal provider/shape/checksum/size failures;
and discard the private file in every non-success path. Directly test header failure,
mid-body failure, injected interruption, validator failure, close failure, and exhausted
retry with exact one-call/one-attempt identities, classes, start/end ordering, and zero
private residue.

### 5. Coinalyze descriptor recovery and terminal equality are still incomplete

The normal path stores `parsed["retrieved_at"]` in the charge descriptor but calls
`complete()` with a new current timestamp. The supposedly exact descriptor and completion
therefore disagree on every ordinary request. `settle_existing_charge()` compares only
digest and bytes. Terminal verification compares digest, bytes, outcome, status, HTTP status,
and points, but not request proof, retrieval URL/status/time, revision JSON, creation fact,
or exact transition history against the exact plan and completion.

Use the descriptor's exact retrieval and revision facts for normal completion and recovery.
Validate its request proof and redacted request shape against the plan on every path. A
settled descriptor must already have the exact completion; a published descriptor may
atomically create only that exact completion and settled transition; a reserved descriptor
may only publish or append an authenticated refund. Terminal success must prove every field
and the exact transition sequence for each of exactly 569 settled liquidation identities,
not only a row count and aggregate byte equality. Add all crash-boundary, zero-point,
200/404, proof, retrieval, revision, transition, and per-identity contradiction regressions.

### 6. Retained and inventory source authority is incomplete

The raw retained source is now reopened and compared to the content inode, which is retained.
The retained sidecar source is not reopened on resume or verify, its live bytes are not
compared with `retained_sidecar_digest`, and the immutable plan retrieval fact is not compared
with the completion. These reads also bypass the retained root descriptors. Reopen and rehash
both raw and sidecar sources through the session roots, reparse both destination and source
sidecar/ZIP bytes, require live device/inode lineage, and compare every immutable retained
path, digest, byte, retrieval, revision, 73-key membership, and five exact cost-key fact.

The inventory replay now rejects duplicate native identities, but it rebuilds only the
accepted subset and ignores additional valid Binance-perpetual mappings in the retained
inventory. Require equality with the complete accepted native/provider mapping set, rejecting
duplicates, conflicts, missing rows, and extra valid mappings. Add the complete retained
missing/replaced/copied raw, changed sidecar source, missing inode, label membership, exact
cost-key, and inventory-set regressions from review 293.

### 7. Terminal proof, archive closure, and boundedness remain incomplete

`verify_state()` authenticates the old head but never requires current watermarks to equal an
authenticated recovered head. It can provider-validate and publish a complete terminal
manifest from crash-tail rows that no immutable run receipt sealed. Require the terminal
state and ledger to equal the authenticated head exactly and bind the terminal receipt to the
chain identity. Include enough accepted authority/ledger material for the streamed manifest
to reconstruct the digest it claims.

The terminal row equation, attempt fact, plan payload, charge transition, seal row, and
post-close private cleanup are now present and should be preserved. However,
`iter_open_charges()` still calls `fetchall()` and its caller wraps the iterator in `list()`;
the production boundedness regression remains too small to detect a universe-sized
collection. Stream recovery and prove bounded production behavior with sufficiently large
instrumented synthetic input.

ZIP open/read errors are typed, but `archive.close()` and the outer file-handle close remain
outside the typed mapping. Map expected archive/member/close failures to bounded acquisition
errors and add unsupported-compression and close-failure coverage alongside the member-count
and uncompressed-byte ceilings.

### 8. The regression drop is materially incomplete

The test count rose from 88 to 95. The added direct tests cover a non-regular lock, the
`BoundRoots` helper in isolation, an extra SQLite view, and a few expanded local checks. They
do not cover most of the explicit review-293 matrix above. The ancestor test also discards
the fd returned by `os.open()` without closing it. Complete the regression matrix before
using the targeted command. Synthetic tests remain deterministic, temporary-rooted,
zero-network, and free of real sleep.

## Consolidated correction authorization

Grok Build remains the sole senior actor for this coherent rewrite and may edit exactly:

1. `src/cryptofactors/acquisition/binance_usdm_harmonic_acquisition.py`
2. `scripts/research/acquire_binance_usdm_harmonic_release.py`
3. `tests/acquisition/test_binance_usdm_harmonic_acquisition.py`

Preserve accepted authority, scope, counts, bytes, capacity, ADR-0029 layer boundaries, and
the working corrections named in this review. Do not edit any other path and use no Git.
This is still implementation refinement within ADR-0029; no new ADR is authorized.

No test may run until every source correction and direct regression above is present. Then
Grok may use the exact review-291 targeted pytest command and repair only failures within
this contract. The limit remains at most three total targeted runs across the review-293 and
review-294 continuation; any command already run counts even though no result was supplied.
Stop on a pass, the third nonzero result, an architecture ambiguity, out-of-scope work,
unsafe repository state, or any real network/data access. Run no Ruff, control,
qualification, sizing, capacity, real plan/acquire/verify, network, Git, or other command.

Stop once with final hashes, line and test-function counts, exact three-path scope, every
authorized command result including any command already run, and the corrected original
shared exception type/cause. Hermes retains integration, broader tests/acceptance commands,
evidence, and developer-source Git. No real plan, data, Gate 3, normalization, catalog,
NautilusTrader, Harmonic Trader, PAPER/LIVE, or next ticket is authorized.

## Reviewer publication scope

The reviewer may stage, commit, and push exactly this review, `docs/handoff/CURRENT_TASK.md`,
and `tickets/CEX-002.md`. Developer source/test paths, real state/data/evidence, and unrelated
dirty work are excluded.
