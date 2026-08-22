# CEX-002 Path-Bound Recovery Correction Review

**Date:** 2026-08-22
**Reviewer:** Lead Quantitative Finance Researcher/Engineer
**Decision:** `REJECTED_CORRECTION_REQUIRED`
**Gate 1:** Source finding remains accepted; affected publication authority is suspended
**Gate 2:** Not accepted

## Reviewed drop

Claude changed the two paths authorized by review 197:

| Path | SHA-256 |
|---|---|
| `src/cryptofactors/acquisition/binance_usdm_harmonic_qualification.py` | `efd8d15d0cdf0c00e36ad01528ab4ef6331aef11d0303cc675ab63b168999852` |
| `tests/acquisition/test_binance_usdm_harmonic_qualification.py` | `3e3bc9892c1be04cd91e235ee5f470496da5f9ec36472b3e923b5074c2e9138e` |

The test path contains 315 `def test_` functions. The reviewer performed read-only
source inspection and an exact-path Git whitespace check. The reviewer ran no test,
linter, repository-control, qualification, sizing, network, or data-mutation command;
the whitespace check is not integration or acceptance evidence.

The drop correctly closes zero-match authority, binds lookup to an exact singleton,
migrates the affected direct-lookup tests, excludes rejected rows from the named
planning/accounting consumers, and separates logical-key, unique-object, and unique-byte
counts. Those corrections must be preserved. Two execution-boundary defects still block
integration.

## Findings

### 1. Critical - rejected-plan preflight occurs after durable writes

The locked-plan check is inside the acquisition loop, but ordinary execution reaches it
only after `metadata_store.commit()`, `ledger.flush()`, and the plan-path atomic write.
The fresh-plan branch can also preserve a legacy plan and flush a new lock before the
check. This does not implement review 197's requirement to fail before reuse or mutation.

Preflight every executable plan entry against `rejected_retained` as soon as that plan is
known and before any durable artifact is created, preserved, committed, flushed, or
rewritten. Existing-lock and migrated-lock execution must reject before reconciliation is
persisted, metadata commit, ledger flush, or plan publication. A fresh plan must reject
before legacy-plan backup, lock publication, ledger publication, metadata commit, or plan
publication. Candidate-only and reviewed-migration read-only phases must remain
non-executing and preserve their existing semantics.

### 2. High - the integration tests contradict the execution boundary and can skip it

`_ambiguity_index()` returns the first monthly mark-price key. With the three contiguous
months in this fixture, deterministic early/middle/recent planning selects that first key.
`test_a_persisted_ambiguous_row_is_rejected_end_to_end` seeds it before the first run, so
production must raise the rejected-plan error and cannot return the report the test then
inspects.

The separate locked-plan test conditionally calls `pytest.skip()` if the fixture does not
select the key, and it checks only progress and lock bytes. It therefore does not prove
the required boundary for ledger, plan, metadata, retry, or other durable authority
artifacts. Make plan membership deterministic with an assertion, never a skip. Snapshot
the complete pre-existing mutable control surface, and instrument or otherwise prove that
no durable write occurs before the exception.

Use two distinct scenarios. The fail-closed scenario must seed a known executing-plan key
and expect the exception before writes. The report-exclusion scenario must seed an
ambiguous candidate-domain key that is deterministically outside the executing plan so a
report can be returned and can prove rejection in resume evidence, manifest
consumability/pending evidence, and production storage credit.

### 3. High - the duplicate-byte test does not exercise production credit

The two-key/one-digest fixture is sound, but its credit result is computed by a second
copy of the loop inside the test. Production could stop deduplicating and that test would
still pass. Route the production credit calculation through one focused helper used by
`run_source_qualification()`, or construct a qualification fixture that reaches the
production report, and assert two valid logical keys, one unique digest, and one byte
charge from that production result.

## Claude correction authority

Sr Dev - Claude Build using Claude Opus 5 is authorized to continue editing only:

- `src/cryptofactors/acquisition/binance_usdm_harmonic_qualification.py`; and
- `tests/acquisition/test_binance_usdm_harmonic_qualification.py`.

Preserve the accepted exact-singleton binding, unbound fail-closed behavior, effective
authority filtering, rejected-lineage reporting, migrated direct-lookup tests, and
separate key/object/byte report fields. Move rejected-plan validation ahead of every
durable mutation in each executing-plan construction/replay path. Replace the
contradictory/skippable tests with deterministic report-exclusion and no-write execution
tests, and make the two-key/one-digest assertion exercise production credit logic.

Do not weaken lookup, hard-code observed production keys, edit sizing paths, implement a
lineage transition, change repository records, or expand scope. Claude runs no test,
linter, control, qualification, sizing, network, data mutation, Git, commit, or push.
Return the two SHA-256 identities and test-function count, then stop for reviewer
inspection.

## Stop boundary

Hermes remains unauthorized. Gate 2 remains unaccepted. No sizing retry, qualification
execution, authority mutation, bulk acquisition, normalization, catalog publication,
NautilusTrader, Harmonic Trader, payoff, PAPER, LIVE, paid-source, reduced-scope, or
next-ticket work is authorized. Next ticket remains `NONE`.
