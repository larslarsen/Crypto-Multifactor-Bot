# CEX-002 Grok Review-294 Noncompliance and Claude Reassignment

Date: 2026-08-25
Reviewer: Lead Quantitative Finance Researcher/Engineer
Decision: REJECTED WITHOUT TESTS; Grok deauthorized and complete correction reassigned
Ticket state: IN_PROGRESS
Next required actor: Sr Dev - Claude Build on Claude Opus 5 when available
Next ticket authorized: NONE

## Inspected correction

The reviewer inspected Grok Build's claimed review-294 completion once at:

- `src/cryptofactors/acquisition/binance_usdm_harmonic_acquisition.py`:
  `eb9ab7b0365c4abac6cee875289a7677fb377065f8486ce2dd3c73b0c5983960`
- `scripts/research/acquire_binance_usdm_harmonic_release.py`:
  `bb6038559d45bddfb011925ad96eb9552cbe4b71bfd5051375adbdcd3de555a9`
  (unchanged)
- `tests/acquisition/test_binance_usdm_harmonic_acquisition.py`:
  `78cc289bbe5115902c7c9d6a46ca65368012780fd7689c4421a70af8d3edfbc2`

The source, CLI, and test file contain 7,530, 151, and 2,747 lines. The test source has
101 test functions. No developer command result was supplied. The reviewer ran no test or
acceptance command because the source contains an ordinary-path schema error and materially
omits the authorized correction.

## Decision

Reject the drop as material noncompliance with review 294. Preserve the useful local
corrections: explicit response-close propagation, byte-bounded diagnostics, single-record
close-failure handling, pre/post SQLite leaf checks, append-only charge transitions,
streamed open-charge iteration, normal-path Coinalyze retrieval reuse, retained sidecar
source hashing, terminal unsealed-tail refusal, terminal chain-head identity, ZIP close
typing, and the six added mutation tests.

Those changes do not form the complete authorized contract. Most operational paths still
bypass the retained roots, the run-seal rows are not authenticated or published as evidence,
the receipt check still trusts only a head and one predecessor, released charges cannot be
retried correctly, the sealed ledger is false after a refund, exact descriptor/inventory
proof remains incomplete, and almost all required direct regressions are absent. The new
schema also fails on every open before any of those mechanisms can execute.

Grok has now returned two partial corrections against the same complete static contract.
Continuing with the same actor is not an efficient use of senior review or model usage.
Review 294 remains the complete correction contract; this review records the concrete
noncompliance and reassigns its implementation to Claude Build when Claude is available.

## Immediate ordinary-path failure

`run_metadata.receipt_sha256` was removed from `SCHEMA_SQL`, but `DOMAIN_CHECKS` still runs:

```sql
SELECT 1 FROM run_metadata ... receipt_sha256 ...
```

Every `AcquisitionState.open()` calls `authenticate_domains()` and therefore raises
`sqlite3.OperationalError: no such column: receipt_sha256`. Correct the schema/domain pair
and add a direct fresh-open regression. Do not mask or broadly wrap the SQLite error.

## Review-294 requirements still missing

### 1. Root capability remains partial

`load_authority_bundle()` has no `BoundRoots` parameter. Authority, helper, code, manifest,
retained adoption, new response temporary/content paths, charge recovery, Binance sidecar
validation, and terminal manifest creation/publication still use pathname-root helpers.
`discard_private()`, `publish_private_file()`, `stream_to_private()`,
`adopt_same_device_file()`, acquisition functions, and `_publish_terminal_manifest()` cannot
accept the session capability. `adopt_retained()` and charge reconciliation explicitly call
the shared validator with `roots=None`. The added ancestor test exercises only the helper,
not a bound plan/acquire/verify session.

Thread one retained session capability through every authority, capacity, state, temporary,
content, retained-source, receipt, recovery, cleanup, and terminal operation exactly as
review 294 requires. Add full-session ancestor rename/swap and operation-specific escape
tests. No pathname fallback is allowed inside a bound production session.

### 2. State setup cleanup remains incomplete

Pre-existing WAL/SHM descriptors are local variables until after `sqlite3.connect()` and
the journal setup. A connect, pragma, identity, or mismatch failure can leak one or both;
the mismatch branches also do not close every remaining local. Put all pre/post descriptors
under one cleanup owner, prove database/WAL/SHM device and inode identity as applicable, and
add the missing WAL/SHM symlink, journal fallback, connect/setup failure, nested-close, and
contention regressions.

### 3. The receipt/run-seal chain is still self-asserted

`run_seal` is not included in the sealed prefix or its watermarks. Recovery selects only its
latest `receipt_sha256` and does not compare the row's predecessor, prefix, or marks with the
receipt. The terminal manifest neither counts nor emits `run_seal`. `authenticate_prefix()`
still rehashes only the head and one predecessor; it does not walk to the installed plan
receipt, compare canonical receipt bytes, validate receipt schema/authority, or compare the
receipt's high-watermarks exactly with the head. Receipt lookup also bypasses `BoundRoots`.

Implement review 294's non-cyclic append-only run/seal representation as an authenticated
chain, validate every seal field and monotone exact watermark, walk the complete lineage to
the installed plan receipt, and stream the seal-link facts into terminal evidence. Tampered,
missing, forked, reordered, over-watermarked, noncanonical, or wrong-schema receipts must
fail resume and verify in independent tests.

### 4. Append-only refund handling is not resumable and its digest ledger is wrong

The descriptor remains unique by `(provider, identity)` after a `RELEASED` transition.
A later legitimate response normally has a new retrieval timestamp, so `reserve_charge()`
finds the released descriptor and raises a revision conflict rather than making a new exact
reservation. Even if every other field repeated, it returns without restoring the ledger or
appending a new reserved transition.

The sealed prefix computes its ledger section by summing every descriptor through
`charge_hi`, including released descriptors. The live singleton equation correctly excludes
released identities. A refund therefore makes the receipt prefix claim a different charged
value from the actual ledger. Represent immutable charge generations explicitly, derive the
active ledger at the paired descriptor/transition watermarks, and prove exact legal sequences
for reserve, publish, settle, release, and a later retry. Add the complete review-294 crash,
refund/retry, descriptor, proof, retrieval, revision, and 200/404 regressions.

### 5. Exact domains and terminal descriptor equality remain incomplete

The new SQL checks use `json_valid()` but do not prove canonical JSON. Timestamp checks are
only loose `LIKE` patterns. Provider/kind, completion/sidecar, attempt class/status,
transition ordering, run/seal, integer, predecessor, and watermark relationships remain
partial. Terminal verification still omits request proof, retrieval URL/status/time, exact
revision JSON, created fact, and legal transition history from each per-identity charge
comparison. Implement the complete field and cross-row domains from review 294 before any
network scheduling or terminal publication.

### 6. Retained inventory equality is still a subset check

Raw and sidecar source hashing improved, but initial adoption and completed sidecar content
validation still bypass the session roots. `_reparse_inventory_mappings()` filters rebuilt
inventory to accepted native names and therefore still ignores an extra valid perpetual
mapping. Require complete accepted inventory equality and the exact retained source,
destination, membership, byte, inode, sidecar, retrieval, and five-cost-key proof. Add every
missing/replaced/copied/extra/missing direct regression specified in review 294.

### 7. Regression delivery remains materially incomplete

Only six tests were added. There are still no direct WAL/SHM/journal/setup-close tests;
complete-chain, `run_seal`, predecessor, high-watermark, canonical receipt, or receipt-fork
tests; exact call/attempt header, interruption, validator, close, and exhaustion tests;
refund/retry and complete charge-descriptor tests; retained source/membership and extra
inventory tests; unsupported-compression/close injection tests; or large instrumented
production boundedness proof. The helper-only ancestor test is not the required session test.

Complete the entire review-294 regression matrix. Tests remain synthetic, deterministic,
temporary-rooted, zero-network, and free of real sleep.

## Claude correction authorization

Claude Build is authorized, when available, to implement review 294 plus the exact residuals
above in only:

1. `src/cryptofactors/acquisition/binance_usdm_harmonic_acquisition.py`
2. `scripts/research/acquire_binance_usdm_harmonic_release.py`
3. `tests/acquisition/test_binance_usdm_harmonic_acquisition.py`

Preserve all accepted authority, economic scope, counts, bytes, capacity, ADR-0029 layer
boundaries, and the useful corrections enumerated in this review. Do not edit any other path
and use no Git. This is implementation refinement within ADR-0029, not a new architecture.

No test may run until the entire source and regression contract is present. Claude may then
run the exact review-291 targeted pytest command and make contract-bounded repairs, at most
three total runs for Claude's continuation. Stop on a pass, the third nonzero result, an
architecture ambiguity, out-of-scope work, unsafe repository state, or any real network/data
access. Run no Ruff, control, qualification, sizing, capacity, real plan/acquire/verify,
network, Git, or other command.

Stop once with final hashes, line and test-function counts, exact three-path scope, every
authorized command result, and the corrected original shared exception type/cause. Hermes
retains integration, broader tests/acceptance commands, evidence, and developer-source Git.
No real plan, data, Gate 3, normalization, catalog, NautilusTrader, Harmonic Trader,
PAPER/LIVE, or next ticket is authorized.

## Reviewer publication scope

The reviewer may stage, commit, and push exactly this review, `docs/handoff/CURRENT_TASK.md`,
and `tickets/CEX-002.md`. Developer source/test paths, real state/data/evidence, and unrelated
dirty work are excluded.
