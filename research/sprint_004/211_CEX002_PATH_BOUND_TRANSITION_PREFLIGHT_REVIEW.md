# CEX-002 Path-Bound Transition Preflight Review

**Date:** 2026-08-22
**Reviewer:** Lead Quantitative Finance Researcher/Engineer
**Decision:** `SOURCE_CORRECTION_REQUIRED`
**Architecture:** ADR-0022 and reviews 208-210 remain controlling
**Gate 1:** Source finding remains accepted; affected publication authority stays suspended
**Gate 2:** Not accepted

## Reviewed correction

Claude edited only the two review-210-authorized paths. The standalone script and the
accepted qualification source/tests remain byte-identical.

| Path | SHA-256 | Decision |
|---|---|---|
| `src/cryptofactors/acquisition/binance_usdm_harmonic_path_bound_transition.py` | `38ab7793424f4bb8256996d07754eba09fd96495eb41bf98d273ac2f387a7439` | Rejected; one preflight proof is missing |
| `scripts/research/apply_binance_usdm_harmonic_path_bound_transition.py` | `ada238d22560ddcaf834dff03d0da44c546856090e6133cf5afeb7be3d50aabd` | Accepted and frozen |
| `tests/acquisition/test_binance_usdm_harmonic_path_bound_transition.py` | `9c54f4a04277ab26821626e2d920e0cc0e5621c000b7ac47db4aab3d9743b2a2` | Rejected; apply-only evidence assertions miss the preflight gap |

The corrected test path contains 25 `def test_` functions. The reviewer performed
read-only static inspection only and ran no test, linter, repository-control, acceptance,
qualification, transition, sizing, network, or data-mutation command.

Review 210's substantive corrections are present and frozen. Fresh state publishes the
four prior artifacts, advanced states rehash and reuse them, resumed execution does not
append a duplicate receipt, completed execution writes nothing, and the interruption
patch is correctly scoped without removing the fixture pins. Review 209's accepted
whole-ledger, branch-specific binding, and streamed gzip proofs also remain intact.

## Finding

### High - advanced preflight does not require all four evidence objects

`preflight()` promises to prove the whole authority state and returns a
`TransitionAuthority`, but its advanced branches prove only the prior lock and ledger
evidence used for structural reconstruction. A missing, substituted, or symlinked prior
report or checkpoint evidence object does not stop `preflight()` from returning
`STATE_LEDGER_ADVANCED` or `STATE_COMPLETE`.

`apply_path_bound_transition()` subsequently calls `resolve_prior_artifacts()` before a
write and therefore catches the damage. That later check does not satisfy review 210's
requirement that the advanced states themselves require all four prior evidence objects,
and it contradicts `preflight()`'s documented altered-evidence rejection contract. The
new parameterized evidence test exercises only `apply_path_bound_transition()`, so it does
not expose the incomplete authority result.

This requires one narrow correction. After an advanced branch has proved its exact lock
and ledger transform, `preflight()` must call the existing no-live-authority
`require_prior_artifacts(paths)` before returning. Fresh preflight must continue to allow
absent evidence because publication has not happened yet. Preserve the immediate
pre-write recheck already performed by `resolve_prior_artifacts()`.

Extend the existing missing/substituted/symlinked evidence matrix to assert that direct
`preflight()` rejects every one of the four evidence objects in both
`STATE_LEDGER_ADVANCED` and `STATE_COMPLETE`, with the store surface unchanged. Retain the
apply-level rejection assertion as the transaction-boundary proof.

## Claude correction authority

Sr Dev - Claude Build using Claude Opus 5 is authorized to edit only:

1. `src/cryptofactors/acquisition/binance_usdm_harmonic_path_bound_transition.py`
2. `tests/acquisition/test_binance_usdm_harmonic_path_bound_transition.py`

This is a bounded preflight correction. Preserve all accepted review-209 and review-210
behavior and tests. The standalone script stays frozen at
`ada238d22560ddcaf834dff03d0da44c546856090e6133cf5afeb7be3d50aabd`.
Do not edit qualification source/tests, the existing qualification CLI, sizing paths,
repository records, controls, or data.

Claude runs no test, linter, control, qualification, transition, sizing, network, data
mutation, Git, commit, push, or repository-record operation. Return the corrected source
and test hashes, unchanged script hash, and test-function count, then stop.

## Stop boundary

Hermes and transition execution remain unauthorized. No ordinary qualification, sizing
source change or retry, acquisition, normalization, catalog publication, NautilusTrader,
Harmonic Trader, payoff, PAPER, LIVE, paid-source, reduced-scope, or next-ticket work is
authorized. Gate 2 remains unaccepted and next ticket remains `NONE`.
