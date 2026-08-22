# CEX-002 Path-Bound Recovery Residual Review

**Date:** 2026-08-22
**Reviewer:** Lead Quantitative Finance Researcher/Engineer
**Decision:** `REJECTED_CORRECTION_REQUIRED`
**Gate 1:** Source finding remains accepted; affected publication authority is suspended
**Gate 2:** Not accepted

## Reviewed drop

Claude changed the two paths authorized by review 198:

| Path | SHA-256 |
|---|---|
| `src/cryptofactors/acquisition/binance_usdm_harmonic_qualification.py` | `166c545c5ce18da3ece4a75c657088823bbdcaba9c8051079906c762a450476d` |
| `tests/acquisition/test_binance_usdm_harmonic_qualification.py` | `d438e630185f489640dc92a79d95730107e5646e6938f463170410202039ae5a` |

The test path contains 314 `def test_` functions. The reviewer performed read-only static
inspection only and ran no test, linter, repository-control, acceptance, qualification,
sizing, network, or data-mutation command.

The drop correctly introduces one production credit-decomposition helper, uses it from
qualification, and tests two valid keys backed by one digest as two keys, one object, and
one byte charge. It also moves the visible branch-local checks ahead of metadata commit,
ledger flush, lock publication, and plan publication. Those changes are accepted and must
be preserved. Two residual defects still block integration.

## Findings

### 1. Critical - existing-lock recovery and reconciliation still precede preflight

The ordinary executing lock is already loaded near the start of qualification, but after
the candidate domain is bound the function calls `recover_retained_samples()` before it
checks that lock's plan. Recovery may call `SampleCheckpointStore.record()` and flush a
valid but previously uncheckpointed retained object.

Later, the non-migrated existing-lock branch calls `ledger.reconcile()` before it rebuilds
the locked plan and calls `_require_no_rejected_plan_entries()`. Reconciliation may settle
a valid outstanding reservation, and `settle()` flushes the ledger. The new test happens
to contain neither an uncheckpointed recoverable valid object nor a reconcilable
reservation, so its empty write list does not cover either reachable mutation.

Once the frozen candidate domain and `rejected_retained` are known, preflight any already
installed executing plan before persistent recovery or reconciliation. Fresh-plan
construction must use in-memory recovery and read-only accounting until its newly built
plan passes the same check; only then may valid recovery and accounting state be
persisted. Candidate-only and reviewed-migration phases retain their existing read-only
or separately governed behavior.

Add a deterministic existing-lock test containing both a valid uncheckpointed recoverable
object and a reconcilable reservation alongside the rejected planned row. The rejection
must occur with no checkpoint record/flush, ledger settle/flush, or other durable write,
and the complete artifact surface must remain byte-identical.

### 2. High - the report-exclusion fixture has no non-planned mark key

The fixture contains exactly the three contiguous months `2020-01`, `2020-02`, and
`2020-03`. The planner selects one early, one middle, and one recent object, so all three
mark-price keys are in the executing plan. Consequently
`next(key for key in mark_keys if key not in planned)` raises `StopIteration`; the report
exclusion assertions are unreachable.

Give this scenario enough same-family candidate objects to leave at least one
deterministically unselected key. Assert that the outside-key set is non-empty before
indexing it, seed that key, and retain the production report assertions for resume,
manifest/pending evidence, storage credit, and unchanged legacy lineage.

## Claude correction authority

Sr Dev - Claude Build using Claude Opus 5 is authorized to continue editing only:

- `src/cryptofactors/acquisition/binance_usdm_harmonic_qualification.py`; and
- `tests/acquisition/test_binance_usdm_harmonic_qualification.py`.

Preserve every correction accepted in reviews 197-199, including exact-singleton binding,
effective authority filtering, migrated direct-lookup tests, rejected-lineage reporting,
separate report quantities, and the shared production credit helper. Move executing-plan
preflight ahead of persistent recovery and reconciling writes, cover both mutation paths
in the no-write test, and make the outside-plan report fixture mathematically possible
and explicit.

Do not weaken lookup, hard-code observed production keys, edit sizing paths, implement a
lineage transition, change repository records, or expand scope. Claude runs no test,
linter, control, qualification, sizing, network, data mutation, Git, commit, or push.
Return both SHA-256 identities and the test-function count, then stop for reviewer
inspection.

## Stop boundary

Hermes remains unauthorized. Gate 2 remains unaccepted. No sizing retry, qualification
execution, authority mutation, bulk acquisition, normalization, catalog publication,
NautilusTrader, Harmonic Trader, payoff, PAPER, LIVE, paid-source, reduced-scope, or
next-ticket work is authorized. Next ticket remains `NONE`.
