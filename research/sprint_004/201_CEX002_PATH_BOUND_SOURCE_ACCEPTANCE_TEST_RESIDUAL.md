# CEX-002 Path-Bound Source Acceptance and Test Residual

**Date:** 2026-08-22
**Reviewer:** Lead Quantitative Finance Researcher/Engineer
**Decision:** `SOURCE_ACCEPTED_TEST_CORRECTION_REQUIRED`
**Gate 1:** Source finding remains accepted; affected publication authority is suspended
**Gate 2:** Not accepted

## Reviewed drop

Claude changed the two paths authorized by review 200:

| Path | SHA-256 | Decision |
|---|---|---|
| `src/cryptofactors/acquisition/binance_usdm_harmonic_qualification.py` | `2f88ad6e7cfc531fefe3d9c7a9ddbc830741687e93c51450fc826062dffb2c74` | Accepted and frozen |
| `tests/acquisition/test_binance_usdm_harmonic_qualification.py` | `d1eb162e26b757d7472ac23816a2ff2c0346084bc57a5d43b5d62e7aca2d19ad` | Rejected; test-only correction required |

The test path contains 315 `def test_` functions. The reviewer performed read-only static
inspection only and ran no test, linter, repository-control, acceptance, qualification,
sizing, network, or data-mutation command.

Production now uses the combined in-memory recovery view consistently for fresh-plan
bootstrap, retained snapshot, and plan construction; persists that exact recovery set
only after plan preflight; preflights installed plans before recovery/reconciliation; and
routes credit through the accepted key/object/byte helper. The production source is
accepted at the exact hash above and may not change in the residual pass.

## Findings

### 1. High - both purportedly unique recovery fixtures use colliding Kline basenames

The no-write test chooses an unplanned `indexPriceKlines` key from the four-family
ambiguity index. Its basename is also present under regular, premium-index, and mark-price
Kline full paths in the actual frozen candidate domain. The test obtains a non-`None`
lookup only by binding a synthetic singleton domain containing that one key, which is not
the domain production binds. Production correctly refuses this recovery, so it does not
exercise the pre-preflight checkpoint-write path.

The fresh-plan test has the same problem. `_kline_manifest_index()` contains monthly and
daily Kline paths with identical basenames for the seeded interval. The complete domain
therefore has two candidates, so ADR-0022 correctly refuses recovery and the object must
be fetched. The assertions expecting `reuse_retained` and no fetch are unreachable.

Use a candidate family whose basenames are genuinely unique across the complete fixture
domain, such as a sufficiently wide monthly funding-rate family. For the no-write test,
select a deterministic unplanned key from that family, retain its object and sidecar
without checkpointing it, bind the complete fixture candidate domain in the precondition,
and prove lookup succeeds there. Keep the rejected planned Kline and reconcilable
reservation in the same test.

For the fresh-plan/rerun test, seed a basename-unique retained funding-rate object before
the first lock. Assert the first plan uses `reuse_retained`, the frozen retained snapshot
contains its exact object and sidecar digests and byte size, and
`budget_snapshot.cumulative_spent_max_bytes_at_lock` equals the expected unique retained
bytes. The current `first.budget["cumulative_spent_max_bytes"] >= 0` assertion is vacuous
and must be removed. Then prove the immediate rerun preserves the same plan inputs,
snapshot, and no-fetch result.

## Claude test-only authority

Sr Dev - Claude Build using Claude Opus 5 is authorized to edit only:

- `tests/acquisition/test_binance_usdm_harmonic_qualification.py`.

The production source must remain byte-identical at
`2f88ad6e7cfc531fefe3d9c7a9ddbc830741687e93c51450fc826062dffb2c74`.
Replace only the two invalid uniqueness fixtures and the vacuous accounting assertion as
specified above. Preserve every other accepted review-197 through review-201 test and
behavior.

Claude runs no test, linter, control, qualification, sizing, network, data mutation, Git,
commit, or push. Return the unchanged production hash, corrected test hash, and
test-function count, then stop for reviewer inspection.

## Stop boundary

Hermes remains unauthorized. Gate 2 remains unaccepted. No sizing retry, qualification
execution, authority mutation, bulk acquisition, normalization, catalog publication,
NautilusTrader, Harmonic Trader, payoff, PAPER, LIVE, paid-source, reduced-scope, or
next-ticket work is authorized. Next ticket remains `NONE`.
