# CEX-002 Claude Review-295 Complete Static Rejection

Date: 2026-08-25
Reviewer: Lead Quantitative Finance Researcher/Engineer
Decision: REJECTED WITHOUT TESTS; consolidated correction remains with Claude Build
Ticket state: IN_PROGRESS
Next required actor: Sr Dev - Claude Build on Claude Opus 5
Next ticket authorized: NONE

## Inspected correction

The reviewer performed one complete static review of Claude Build's claimed reviews 294-295
correction at:

- `src/cryptofactors/acquisition/binance_usdm_harmonic_acquisition.py`:
  `e848d31555a788d11c259eeaf742be7b35f4c5e7b1133f537e6e6c01db28ed78`
- `scripts/research/acquire_binance_usdm_harmonic_release.py`:
  `bb6038559d45bddfb011925ad96eb9552cbe4b71bfd5051375adbdcd3de555a9`
  (unchanged)
- `tests/acquisition/test_binance_usdm_harmonic_acquisition.py`:
  `d366aa90d907acbe1e66a2212867b350be17d0c38d28009ee30299a26ea098bd`

The source, CLI, and test files contain 8,228, 151, and 3,308 lines. The test source has
122 test functions. No developer command result or original exception/cause was supplied.
The reviewer ran no test or acceptance command because static review found material
capability, recovery, domain, and evidence omissions.

## Decision

Reject the drop without another reviewer test cycle. Preserve its useful corrections: the
fresh schema/domain pair now agrees; state-owned WAL/SHM descriptors close on setup failure;
charge generations permit refund and retry; the sealed ledger is derived at paired charge
and transition marks; JSON and UTC helpers are exact; inventory comparison now uses the
complete mapping count and digest; receipt reads are canonical and descriptor-bound; the
chain walks to the installed plan receipt; terminal verification handles the non-cyclic
current seal link explicitly; seal links are streamed into terminal evidence; and 21 focused
tests were added.

Those changes do not complete reviews 294-295. The bound session still reopens trusted
authority through pathnames, rollback-journal and session-cleanup failure paths remain
unsafe, the current receipt/seal link does not authenticate the run or receipt document,
publish-before-link recovery is impossible, open-charge recovery can seal an inexact
descriptor, transport errors contradict their own domain, terminal evidence cannot
reconstruct the prefix, and the required direct regression matrix remains incomplete.

Claude remains the authorized senior actor because these are architecture-sensitive
capability, crash-recovery, and financial-ledger corrections and Grok was deauthorized by
review 295. Implement every item below as one correction before running the targeted suite.

## Complete residual correction

### 1. The retained session capability still has pathname fallbacks

`load_authority_bundle(..., roots=roots)` calls `authenticate_helpers()`, `code_identity()`,
`load_attestation()`, `load_holdout()`, `resolve_cost_objects()`, and
`derive_coinalyze_mappings()` without forwarding `roots`. `module_sha256()` and
`code_identity()` also make pathname `is_file()`/`is_symlink()` prechecks, while
`resolve_cost_objects()` uses pathname `is_file()`, `is_symlink()`, and `resolve()` before
its descriptor read. Initial retained adoption calls the qualification module's
`retained_credit_decomposition()` and `verify_retained_object()`, which use pathname
existence, hashing, sidecar, and stat operations.

`open_parent_dir()` and `open_dir_chain()` deliberately fall back to opening a new pathname
root when a path is outside the repository/store capabilities. Reviews 294-295 prohibit
that fallback inside a bound production session. Reject an out-of-capability override or
bind its accepted root explicitly before any read or write; do not silently reopen it.

Forward one capability through every authority and retained operation, replace the imported
pathname retained proof with acquisition-owned descriptor proof, and remove all bound-path
prechecks. The session test swaps the store only at `before_raw_publication`, after every
authority read, so it cannot detect these defects. Add authority, retained-source, receipt,
temporary, terminal, and operator-override swaps/escapes that prove the actual operation,
not only a later content write.

### 2. SQLite rollback-journal and post-bind cleanup remain unsafe

`AcquisitionState.open()` pre-proves only `-wal` and `-shm`. It never proves a pre-existing
`-journal` leaf before SQLite may use it. The new fallback test substitutes a PRAGMA result;
it does not install a rollback-journal symlink or prove its device/inode lifecycle. Extend
the single cleanup owner and pre/post identity rules to the rollback journal and add the
direct symlink and setup-boundary regressions required by review 294.

After `bind_session()` succeeds, both `run_acquire()` and `verify_state()` call
`_cleanup_partials()` before entering the `try/finally` that closes state and `BoundRoots`.
A cleanup/open/unlink failure therefore leaks the writer lock, SQLite resources, and root
descriptors. Put every post-bind action under the session owner immediately and directly
inject cleanup failure in plan/acquire/verify as applicable, proving one typed error and a
subsequent writer can bind.

### 3. The latest receipt/seal link is not an exact authenticated run record

The current `run_seal` row is intentionally one row beyond `seal_head.seal_hi` to avoid a
self-hash cycle. That can be valid only if the content-addressed receipt independently and
exactly authenticates the whole current link. It does not. Run receipts carry no `run_id`,
and `_validate_receipt_document()` checks only schema, ticket, policy, and plan identity.
It does not compare the receipt's authority, code, run timestamps, stop reason, attempt and
network counts, deltas, capacity facts, or other accepted fields with `run_metadata`, state,
and the seal link. `_walk_chain()` likewise does not compare each historical seal's run id,
predecessor, marks, and prefix with its receipt.

Give the run receipt an exact immutable run identity and validate every accepted receipt
field and exact document key set. Bind the current out-of-prefix seal row to that receipt,
and bind every historical seal row while walking the complete lineage. Add independent
wrong-run, wrong-authority/code, wrong-schema, extra/missing field, predecessor, mark,
prefix, counter, timestamp, stop-reason, and reordered/forked-link regressions.

There is also no recovery for a crash after `write_named_receipt()` and before the
`run_seal` insert. `_recover_published_receipt_head()` consults only `run_seal`, then rejects
any finished `run_metadata` row with no seal. Implement the review-293/294 recorded-receipt
recovery boundary so a legitimate published receipt is located through bound receipt roots,
fully validated, linked once, and advanced by predecessor CAS. Missing, ambiguous, or
malformed candidates fail closed. Add fault points and direct tests before/after receipt
publication, seal-link insertion, and head advance.

### 4. Open-charge recovery can seal an inexact descriptor

When a published charge already has a completion, `reconcile_open_charges()` calls
`settle_existing_charge()`, which compares digest, bytes, outcome, status, points, and
retrieval time but omits request proof, exact retrieval URL/status/document, exact revision,
created fact, and exact transition history. When completion is absent, recovery checks the
request proof and body but still does not require the exact retrieval URL/status/document or
the exact revision document before creating a completion. `verify_state()` later uses a
query substring test instead of exact accepted retrieval URL equality. A malformed crash
tail can therefore be settled and included in a new receipt before terminal verification
eventually rejects it.

Centralize one exact plan/descriptor/completion validator and use it before every publish,
settle, recovery, seal, and terminal boundary for both 200 and 404. Require exact document
keys, canonical values, request proof, redacted URL, status, UTC retrieval/creation order,
revision, points/outcome, generation, bytes/digest, and legal transitions.

The domain query claiming every charge has a transition joins only provider/identity, not
generation. `open_charge_count()` has the same missing generation predicate. Correct all
generation joins and prove a missing-transition newest generation, duplicate/illegal
history, contradictory 200/404 descriptor, and every recovery crash boundary independently.

### 5. Attempt and state domains still contradict executable paths

`request_with_retry()` records a transport-raised `AcquisitionError` as `RETRY_TERMINAL`
with `status_code=NULL`. `DOMAIN_CHECKS` rejects every terminal attempt with a null status.
The first such call therefore persists state that the next open refuses, and it still does
not implement review 293's transport-versus-validation distinction. Introduce an exact
typed retryable transport/read failure or an accepted statusless transport classification;
terminal provider/validation errors and retryable transport errors must not share a domain.

Complete the remaining field and cross-row domains: exact provider/kind combinations;
per-generation descriptor/transition existence; exact attempt ended/class/status/fact
relationships; run end/order/stop/counter domains; and exact seal predecessor, run, marks,
and watermark relationships. Add direct header failure, injected interruption, validator
failure, response-close failure, exhausted retry, and transport-raised typed-error tests.
Each actual call must still produce exactly one attempt with the original bounded cause.

### 6. Retained proof and its regressions remain incomplete

The later shared validator now reopens retained raw and sidecar sources through `BoundRoots`
and proves live raw inode lineage. Preserve that. Initial decomposition and per-object
verification are still pathname-based as described above. The recorded `source_device` is
never compared back to the live source device, and the immutable plan still lacks the exact
sidecar source byte/revision facts required by review 293.

Bind and prove the raw and sidecar source digest, bytes, retrieval/revision, device/inode,
destination, exact 73-key membership, and exact five cost keys at adoption, every resume,
and verify. Add missing/replaced/copied raw, changed sidecar source, missing/altered inode and
device fields, extra/missing retained label, and each count/byte/cost-key invariant as
independent tests.

The inventory implementation now compares the complete perpetual mapping count and digest,
but `test_an_extra_retained_inventory_mapping_is_refused` overwrites content at its old
digest path. It therefore fails at the content-address check before proving mapping-set
equality. Construct internally consistent mutated content/plan evidence or call the exact
mapping validator directly so an extra valid perpetual mapping is the isolated failure.

### 7. Terminal evidence and boundedness are not independently proved

The terminal manifest emits the mutable head, plans, completions, sidecars, charges,
transitions, attempts, runs, seal links, and gaps, but no authority record and no explicit
ledger fact. It cannot reconstruct `_prefix_digest_unlocked()` because that digest begins
with full authority/pins/code/destination/device/creation data. Emit the exact accepted
authority and enough paired-watermark ledger material to reconstruct both the authenticated
head prefix and terminal semantic digest. Make row equations cover those records and add an
independent streaming reconstruction test.

The new large-run test scans Python GC containers and heuristically excludes fixture ids; it
does not instrument cursor, queue, parser, manifest, receipt, or validator maxima and can
miss a universe-sized retained collection. Replace or supplement it with deterministic
production-path instrumentation that proves the accepted batch/queue/sample/token/row
ceilings while processing a materially larger synthetic universe.

## Claude correction authorization

Claude Build is authorized to implement reviews 294-296 in only:

1. `src/cryptofactors/acquisition/binance_usdm_harmonic_acquisition.py`
2. `scripts/research/acquire_binance_usdm_harmonic_release.py`
3. `tests/acquisition/test_binance_usdm_harmonic_acquisition.py`

Preserve all accepted authority, economic scope, counts, bytes, capacity, ADR-0029 layer
boundaries, and the useful corrections enumerated above. Do not edit any other path and use
no Git. This is completion of the accepted architecture, not authorization to redesign its
economic or source semantics.

No test may run until every source item and its direct regression are present together.
The reviews 295-296 targeted allowance is cumulative: at most three executions of the exact
review-291 pytest command, counting any run already made even if it was omitted from the
return. Claude may make contract-bounded repairs between those runs. Run no Ruff, control,
qualification, sizing, capacity, real plan/acquire/verify, network, Git, or other command.
Stop on a pass, the third cumulative nonzero result, architecture ambiguity, out-of-scope
work, unsafe repository state, or any real network/data access.

Stop once with final hashes, line and test-function counts, exact three-path scope, every
authorized command and result including the cumulative run number, and the original shared
exception type/cause for any failure. Hermes retains integration, broader tests/acceptance
commands, evidence, and developer-source Git. No real plan, data, Gate 3, normalization,
catalog, NautilusTrader, Harmonic Trader, PAPER/LIVE, or next ticket is authorized.

## Reviewer publication scope

The reviewer may stage, commit, and push exactly this review, `docs/handoff/CURRENT_TASK.md`,
and `tickets/CEX-002.md`. Developer source/test paths, state/data/evidence, and unrelated
dirty work are excluded.
