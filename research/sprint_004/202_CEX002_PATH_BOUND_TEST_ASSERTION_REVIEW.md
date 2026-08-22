# CEX-002 Path-Bound Test Assertion Review

**Date:** 2026-08-22
**Reviewer:** Lead Quantitative Finance Researcher/Engineer
**Decision:** `TEST_CORRECTION_REQUIRED`
**Gate 1:** Source finding remains accepted; affected publication authority is suspended
**Gate 2:** Not accepted

## Reviewed drop

| Path | SHA-256 | Decision |
|---|---|---|
| `src/cryptofactors/acquisition/binance_usdm_harmonic_qualification.py` | `2f88ad6e7cfc531fefe3d9c7a9ddbc830741687e93c51450fc826062dffb2c74` | Unchanged, accepted, and frozen |
| `tests/acquisition/test_binance_usdm_harmonic_qualification.py` | `c401cdaaaa1999314c4388be529066849d0a51e1d03504db6bf5fa1f4cf09dad` | Rejected; one assertion correction required |

The test path contains 315 `def test_` functions. The reviewer performed read-only static
inspection only and ran no test, linter, repository-control, acceptance, qualification,
sizing, network, or data-mutation command.

The funding-rate fixtures now prove basename uniqueness against the complete fixture
domain. The no-write case now reaches both deferred mutation paths, and the fresh-plan
case proves exact object/sidecar identities and immediate-rerun stability. One accounting
assertion remains incorrect.

## Finding

### High - lock-time retained accounting is compared with post-execution spend

The fresh-plan test correctly computes `expected_retained_bytes` from the deduplicated
`reuse_retained` checkpoint rows, but only asserts that it is at least the seeded payload
size. It then compares `cumulative_spent_max_bytes_at_lock` with
`first.budget["cumulative_spent_max_bytes"]`. The former is frozen before acquisition;
the latter is reported after the run's planned downloads have been charged. They are not
the same quantity and should differ in this fixture.

Assert instead that `expected_retained_bytes` equals the expected seeded unique bytes and
that `budget_snapshot.cumulative_spent_max_bytes_at_lock` equals
`expected_retained_bytes`. Preserve the existing post-run and immediate-rerun assertions;
do not weaken them or change production.

## Claude test-only authority

Sr Dev - Claude Build using Claude Opus 5 is authorized to edit only
`tests/acquisition/test_binance_usdm_harmonic_qualification.py` and only the accounting
assertion block described above. Production must remain byte-identical at
`2f88ad6e7cfc531fefe3d9c7a9ddbc830741687e93c51450fc826062dffb2c74`.

Claude runs no test, linter, control, qualification, sizing, network, data mutation, Git,
commit, or push. Return the unchanged production hash, corrected test hash, and
test-function count, then stop for reviewer inspection.

## Stop boundary

Hermes remains unauthorized. Gate 2 remains unaccepted. No sizing retry, qualification
execution, authority mutation, bulk acquisition, normalization, catalog publication,
NautilusTrader, Harmonic Trader, payoff, PAPER, LIVE, paid-source, reduced-scope, or
next-ticket work is authorized. Next ticket remains `NONE`.
