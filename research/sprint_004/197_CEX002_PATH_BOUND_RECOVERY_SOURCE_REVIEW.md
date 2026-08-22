# CEX-002 Path-Bound Recovery Source Review

**Date:** 2026-08-22
**Reviewer:** Lead Quantitative Finance Researcher/Engineer
**Decision:** `REJECTED_CORRECTION_REQUIRED`
**Gate 1:** Source finding remains accepted; affected publication authority is suspended
**Gate 2:** Not accepted

## Reviewed drop

Claude changed only the two review-196 paths:

| Path | SHA-256 |
|---|---|
| `src/cryptofactors/acquisition/binance_usdm_harmonic_qualification.py` | `b4c8340006697f84f16e66f57dfc6e5fa9c8d66baa3c27fbc9ec606d396426ed` |
| `tests/acquisition/test_binance_usdm_harmonic_qualification.py` | `0e711739b3f3b282d0690b693d00168f905b6a4abb32a176d034ba4947399c69` |

The test path contains 311 `def test_` functions. The reviewer ran no test, linter,
control, qualification, sizing, network, or data-mutation command.

The drop correctly introduces candidate-domain binding, explicit rejected-lineage
records, separate retained-key/object/byte counts, and fail-closed unbound lookup. It is
not safe for integration because rejected legacy rows can still become authority through
other production paths and existing test expectations were not migrated.

## Findings

### 1. Critical - zero-domain recovered keys remain accepted

`basename_collides()` returns true only when a basename maps to more than one candidate
key. `ambiguous_recovered_rows()` therefore accepts a persisted recovered row whose key is
absent from the bound domain, and `lookup()` can accept an out-of-domain key when called on
an already-bound index. A full-key binding is valid only when the domain entry is exactly
the singleton `{key}`. Both zero and multiple matches must reject.

This matters across resumes because the current candidate domain can differ from the set
of legacy checkpoint rows while the later storage-credit loop scans the whole checkpoint.

### 2. Critical - rejected rows re-enter through raw checkpoint consumers

The new `_checkpoint_row()` and `_evidence_objects()` views exclude rejected rows, but
production continues to pass `checkpoint.objects` into retained snapshots, ledger
bootstrap/reconciliation, and storage-credit iteration. More directly, `planned_new`
checks the raw checkpoint and `_acquire_sample()` reads it again. If a rejected key appears
in the executing plan, its raw `status=complete` row is reused as provider authority.

One effective checkpoint mapping must be the sole authority view for planning, retained
snapshots, manifest proof, budget reconciliation, and credit. Raw checkpoint access is
permitted only for persistence, explicit rejected-lineage reporting, and total-row
observability. A frozen plan that requires a rejected legacy row must fail closed before
reuse or mutation unless a separately reviewed lineage-preserving transition has replaced
that row; ordinary execution may not silently overwrite it.

### 3. High - existing direct-lookup tests now fail statically

`lookup()` deliberately returns `None` while unbound, but existing tests still assert a
non-`None` result from an unbound index, including the tampered-sidecar test, the
same-digest recovery helpers, invalid-cost recovery, and migration recovery selection.
Those tests must bind the complete domain relevant to their fixture before lookup. Do not
restore permissive unbound behavior.

### 4. High - the required integration and dedup proofs are absent

The new test named `test_a_persisted_ambiguous_row_is_excluded_from_every_authority_path`
calls only `effective_retained_objects()`. Production does not call that helper, so the
test proves no end-to-end exclusion. The final count test does not construct two valid
logical keys backed by one digest and its comparison against every checkpoint digest does
not prove credit deduplication.

Add a `run_source_qualification()` test which seeds a persisted ambiguous recovery and
proves it is rejected in resume evidence, manifest consumability, planning/source
evidence, and storage credit. Add a separate out-of-domain persisted-row case. Add a
fixture with two independently valid full-key bindings to the same content digest and
prove two retained keys, one unique object, and one byte charge.

## Claude correction authority

Sr Dev - Claude Build using Claude Opus 5 is authorized to continue editing only the same
two source/test paths. Implement the exact-singleton binding rule and route production
through one effective retained-authority view. Ensure no rejected row can re-enter through
plan execution, `_acquire_sample()`, retained snapshots, ledger accounting, manifest
proof, source evidence, or credit. Preserve raw rejected rows as lineage and fail closed
when ordinary execution would need one.

Update every affected existing test to bind its complete fixture domain, and add the
integration, zero-domain, execution-boundary, and real dedup tests above. Do not weaken
unbound lookup, hard-code the observed 17 keys, edit sizing paths, implement the later
source-identity transaction, or change repository records.

Claude runs no test, linter, control, qualification, sizing, network, data mutation, Git,
commit, or push. Return both SHA-256 identities and the test-function count, then stop for
reviewer inspection.

## Stop boundary

Hermes remains unauthorized. Gate 2 remains unaccepted. No sizing retry, qualification
execution, authority mutation, bulk acquisition, normalization, catalog publication,
NautilusTrader, Harmonic Trader, payoff, PAPER, LIVE, paid-source, reduced-scope, or
next-ticket work is authorized. Next ticket remains `NONE`.
