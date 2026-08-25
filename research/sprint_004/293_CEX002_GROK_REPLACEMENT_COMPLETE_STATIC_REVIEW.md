# CEX-002 Grok Replacement Complete Static Review

Date: 2026-08-25
Reviewer: Lead Quantitative Finance Researcher/Engineer
Decision: REJECTED ON COMPLETE STATIC REVIEW; one consolidated correction retained by Grok
Ticket state: IN_PROGRESS
Next required actor: Sr Dev - Grok Build on Grok 4.6 High
Next ticket authorized: NONE

## Inspected replacement

The reviewer inspected Grok Build's complete review-292 replacement once at:

- `src/cryptofactors/acquisition/binance_usdm_harmonic_acquisition.py`:
  `1678a11a3759e38d352c6e2528939e06fbfc85c02422f43f8299166c5304dea4`
- `scripts/research/acquire_binance_usdm_harmonic_release.py`:
  `bb6038559d45bddfb011925ad96eb9552cbe4b71bfd5051375adbdcd3de555a9`
- `tests/acquisition/test_binance_usdm_harmonic_acquisition.py`:
  `1f98b8458da91949f758ddd38bcd98b83655fa973f6ffa3a16cbe591106ac039`

The source, CLI, and test file contain 6,555, 151, and 2,559 lines. The test source has
88 test functions. No developer command result was supplied and the reviewer ran no test
or acceptance command.

## Decision

Reject the replacement as one unit. It is a material improvement over the review-291
snapshot: redirects are disabled; normal streamed reads now occur before an attempt is
recorded successful; attempts have a plan foreign key; queues and `consume_manifest()`
are bounded; Coinalyze charges carry recovery fields and most transitions check row
counts; retained facts enter plan payloads; ZIP and decimal bounds were added; and the
terminal evidence now separates raw, sidecar, and total physical equations.

Those changes are the correction base. They do not close the governing invariants. The
central state digest is still self-asserted mutable SQLite state rather than an immutable
receipt-authenticated prefix, and several recovery and evidence paths accept facts that
the reviewed contract requires them to prove. Passing the current tests would therefore
not authorize integration or real acquisition.

This is one complete static decision. All source and regression corrections below must
be implemented together before any further test command. Do not return a local subset.

## Blocking findings and exact correction

### 1. The state root and authenticated lineage are not durable authority

`AcquisitionState.open()` connects to `/dev/fd/<file-fd>` and then requests WAL mode
without checking the returned journal mode. SQLite still discovers or creates its
adjacent `-wal` and `-shm` names through its database pathname; those files are neither
opened below a retained directory descriptor nor checked no-follow. The accepted store
and repository descriptors are also reopened for each operation, so a renamed or swapped
ancestor can change the session root between authority, capacity, state, and publication
operations. The lock leaf is not proved regular.

Bind the repository and store once per session with retained no-follow directory
descriptors. Perform all descendant access relative to those descriptors. For SQLite,
hold the state-parent descriptor and connect through its stable directory-fd path so the
database, WAL, and SHM remain below that directory; prove the lock/database/WAL/SHM leaves
regular and no-follow where present, hold the root descriptors through close, and require
the `journal_mode` result to be exactly `wal`. Use descriptor `fstat`/`fstatvfs`, not
pathname `stat`, for capacity and inode facts. Add ancestor swap, state/WAL/SHM symlink,
non-regular lock, journal fallback, contention, setup-failure, and nested-close cleanup
regressions.

The `watermark` row is mutable and its `predecessor_receipt_sha256` is never read, hashed,
or opened. `_sealed_digest_unlocked()` omits sidecar facts, charge descriptors and states,
the ledger, unfinished run facts, and the watermark. Its completion prefix is the first
`completion_count` rows in provider/identity sort order rather than a stable insertion
prefix. A legitimate crash-tail completion that sorts earlier can invalidate a prior
seal, while altered sidecar or charge facts can escape it. A run receipt computes its
semantic digest before `finish_run()`, so it does not describe the state subsequently
sealed. `seal_watermark()` then overwrites the only alleged anchor.

Implement an immutable content-addressed run-receipt chain. Each receipt must name and
rehash its predecessor, carry stable high-watermarks for every append-only fact stream,
and carry the digest of exactly that prefix. Add stable sequence identities for
completions, sidecars, charge descriptors/transitions, and runs; attempts already have
one. The SQLite head may be mutable only as a pointer to a no-replace receipt whose bytes
authenticate the stored digest and high-watermarks. On resume, rehash that receipt and
its predecessor link before trusting the prefix. Recover the publish-before-head-update
boundary from the recorded run receipt, and validate/reconcile provider/content-backed
unsealed tail facts before extending the chain. A tail row must never reorder the sealed
prefix.

The semantic digest and sealed prefix must include every accepted field: full authority
and pins, complete plan facts, gaps, completions, sidecars, charges and transitions,
ledger equation, attempts including redacted facts and true start/end times, and all run
facts. Authenticate canonical JSON, UTC timestamps, provider/kind/outcome/status
combinations, request proofs, integer domains, and receipt hashes before use. Reject
extra SQLite tables, indexes, views, or triggers; the current schema check ignores views
and triggers. Tests must independently mutate and delete each sealed fact class and prove
resume and verify refusal. A test that only observes `semantic_digest()` change is not an
authentication test.

### 2. One network call still does not imply one exact durable attempt

`request_with_retry()` increments `network_calls` before `stream_get()`, but both header
and body `FaultInjected` paths leave no attempt. It gives transport-raised
`AcquisitionError` a terminal classification without a transport/validation distinction,
does not preserve actual call start/end times, and records a streamed response `OK` before
sidecar, ZIP, secret, or Coinalyze semantic validation. The run receipt publishes
`network_calls` and `attempt_delta` without requiring equality. The unexpected-worker
message preserves its cause but has no byte bound.

Give every actual call exactly one coordinator-owned attempt fact in all exit paths,
including injected interruption and response close failure. Capture start immediately
before the call and end after close and validation. Distinguish retryable transport/read
failure from terminal checksum, size, request-shape, and provider-semantic failure; do not
durably label a malformed or secret-bearing response `OK`. Discard every failed private
file before retry or return. Require the invocation's network-call count to equal its
durable attempt delta before receipt publication. Preserve the causal exception with a
fixed-size, secret-redacted diagnostic and regression-test header failure, mid-body
failure, injected interruption, validator failure, close failure, and exhausted retry.

### 3. Coinalyze recovery does not reproduce its immutable descriptor

The expanded charge row is useful, but `reserve_charge()` does not compare existing
`retrieval_json` or `revision_json`. Charge domains do not enforce the exact `200`/`404`,
outcome, point, request-proof, time, or canonical-JSON relationships. `complete()` still
allows a `SETTLED` charge with no completion to create one, which is not the strict
`RESERVED -> PUBLISHED -> SETTLED` transition.

Recovery accepts a stored `404` with a contradictory non-unavailable outcome, treats a
stored point count of zero as "not supplied", ignores the stored retrieval time when it
creates the completion, and does not re-prove the request digest. Existing completion
settlement and terminal verification compare counts and aggregate bytes, not each
charge's content digest, bytes, status/outcome, points, request proof, retrieval, and
revision against its exact plan and completion row. The current test that manually rolls
a settled charge back to `PUBLISHED` and expects resume to accept it encodes a forbidden
reverse transition.

Make the descriptor immutable and canonical, compare every field on idempotent replay,
and validate it against the exact plan request. Only an unpublished reservation may be
released; only a published charge may atomically create its exact completion and become
settled; a settled row requires its already-existing exact completion. Recover `200` and
`404` using the stored retrieval and revision facts and reject any internal contradiction.
Terminal success must prove the complete per-identity descriptor/completion/plan equality
for exactly 569 settled liquidations, not only a 569-row join and equal aggregate bytes.
Replace the reverse-transition test with crash-boundary and contradictory-descriptor
regressions.

### 4. Retained credit is not re-proved against the retained source

The plan now carries raw digest/bytes and a sidecar digest, but
`retained_source_path` actually names only the checksum sidecar and is unused. Adoption
records source/content inode fields using pathname `os.stat()`. The shared validator makes
`content_inode` optional, compares only the destination inode to the stored number, and
never reopens the accepted raw source or proves that source and destination are still the
same device/inode. Offline verification can therefore keep the 5,225,416-byte credit
after the source hard-link lineage is removed or copied, and it does not re-prove the
source revision facts.

Bind the exact retained raw and sidecar source paths, digests, bytes, retrieval/revision
facts, and the exact 73-key/five-cost-key membership in immutable plan facts. On every
resume and verify, open source and content through retained root descriptors, rehash both,
and require live `fstat` device/inode equality; inode fields are mandatory evidence, not
optional self-reported values. Reparse the sidecar and ZIP through those descriptors.
Independently test missing/replaced/copied raw source, changed sidecar source, removed
inode fields, an extra/missing retained label, and each exact cost-key invariant.

The retained Coinalyze inventory digest prevents ordinary substitution, but its replay
parser silently overwrites duplicate native identities. Require the exact accepted
native/provider mapping set with conflicting and duplicate identities rejected on every
resume and verify.

### 5. Archive, schema, and publication failures are not fully fail closed

The ZIP checks add the requested path, member, and expansion controls, but member open can
still raise expected archive errors such as unsupported-compression `NotImplementedError`
outside the typed acquisition boundary. The new "bomb" regression tests member count,
not the uncompressed-byte ceiling. Root/session problems above also remain in pathname
`os.stat()` calls and in temporary/terminal setup.

Map all expected ZIP open/read/close failures to a bounded typed acquisition failure and
directly test both member-count and uncompressed-byte ceilings. Keep the numeric lexeme
and duplicate-field bounds, and add exact boundary tests rather than only one exponent
example. No parser/library exception may escape as a generic worker failure.

### 6. Terminal evidence is richer but is not yet an independent exact proof

The terminal manifest omits each attempt's `redacted_fact_json`, each charge's current
transition state, the authenticated receipt predecessor/high-watermarks, and the plan
facts needed to expose retained provenance. Its returned row count is published without
an independently computed exact row equation. A failure after the terminal private file
is closed but before or during no-replace rename still leaves the private file behind.

Stream plan/provider, completion, sidecar, charge/transition, attempt, run/seal, and gap
facts needed to reconstruct the accepted release. Include the full redacted attempt fact
and immutable chain identity. Compute the expected row equation independently from SQL
counts and require equality while the manifest is still private. Keep the separate raw,
sidecar, and total physical equations and the exact 569 descriptor join. Enclose creation,
close, target-open, collision handling, rename, and directory fsync in one cleanup owner
so every non-success removes the private file.

Keep all production queues bounded and all plan/terminal iteration streaming. Replace
the 24-row collection check with a production-path proof whose input is large enough and
whose instrumentation would fail if any universe-sized Python collection were created.
Also bound or stream run and charge fact helpers that currently use `fetchall()` lists.

## Regression decision

The ten added regressions cover useful local behavior but not the governing invariants.
In particular:

- `test_semantic_digest_binds_every_trusted_fact` only recomputes two mutable-state
  digests, the exact anti-test identified by review 291;
- the mutation/deletion test reuses one already-corrupted state instead of independent
  valid fixtures;
- the settled-to-published test requires an invalid reverse transition;
- the redirect test checks only a client flag despite claiming secret-forwarding proof;
- the ZIP "bomb" test checks only member count;
- the streamed-body test does not prove one durable failed attempt plus one retry; and
- the 24-row boundedness test remains too small to detect a universe-sized collection.

Repair or replace those tests and add the direct regressions specified above. Tests stay
synthetic, deterministic, temporary-rooted, zero-network, and free of real sleep.

## Consolidated correction authorization

Grok Build may correct or coherently rewrite exactly:

1. `src/cryptofactors/acquisition/binance_usdm_harmonic_acquisition.py`
2. `scripts/research/acquire_binance_usdm_harmonic_release.py`
3. `tests/acquisition/test_binance_usdm_harmonic_acquisition.py`

Preserve the accepted authority, scope, counts, bytes, capacity basis, ADR-0029 layer
boundaries, and the working improvements enumerated in this review. The immutable seal,
descriptor-root, attempt, charge, retained, and terminal corrections above are one
contract. This is an implementation refinement of accepted ADR-0029, not authorization
to change the architecture or add another ADR. Do not edit any other path and use no Git.

Only after the whole correction and all direct regressions are present may Grok use the
review-291 exact targeted pytest command, with at most three total runs in this
continuation. Stop on a pass, the third nonzero result, an architecture ambiguity, an
out-of-scope requirement, unsafe repository state, or any real network/data access. Run
no Ruff, control, qualification, sizing, capacity, real plan/acquire/verify, network,
Git, or other command.

Stop once with final hashes, test-function count, every authorized command result, the
corrected original shared exception type/cause, and exact three-path scope confirmation.
Hermes retains integration, broader tests/acceptance commands, evidence, and developer
source Git. No real plan, data, Gate 3, normalization, catalog, NautilusTrader, Harmonic
Trader, PAPER/LIVE, or next ticket is authorized.

## Reviewer publication scope

The reviewer may stage, commit, and push exactly this review, current task, and ticket.
Developer source/test paths, real state/data/evidence, and unrelated dirty work are
excluded.
