# CEX-002 Transition Focused Test Failure

**Date:** 2026-08-22
**Reviewer:** Lead Quantitative Finance Researcher/Engineer
**Decision:** `PRODUCTION_STATIC_ACCEPTED_TEST_CORRECTION_REQUIRED`
**Architecture:** ADR-0022 and reviews 208-211 remain controlling
**Gate 1:** Source finding remains accepted; affected publication authority stays suspended
**Gate 2:** Not accepted

## Reviewed correction

Claude made the exact review-211 preflight correction and edited only the two authorized
paths. Advanced `preflight()` now requires all four prior evidence objects before
returning authority, the parameterized evidence matrix checks both direct preflight and
transaction entry, and fresh preflight remains evidence-free.

| Path | SHA-256 | Decision |
|---|---|---|
| `src/cryptofactors/acquisition/binance_usdm_harmonic_path_bound_transition.py` | `f9a1bc89c63b22c974d020044ea8732939358efae00b42f2141bfd0eee34e5e5` | Static review accepted and frozen |
| `scripts/research/apply_binance_usdm_harmonic_path_bound_transition.py` | `ada238d22560ddcaf834dff03d0da44c546856090e6133cf5afeb7be3d50aabd` | Accepted and frozen |
| `tests/acquisition/test_binance_usdm_harmonic_path_bound_transition.py` | `21066eb78cc14ccd15799bb1c34c750e96be7d0128ce6be77f4223fd7db972a2` | Rejected; two mechanical test defects |

The test path contains 26 `def test_` functions and collects 69 cases.

## Owner-authorized focused validation

The owner explicitly authorized the reviewer to run focused synthetic tests instead of
waiting for Hermes. This exception covered the isolated temporary-fixture suite and its
exact-path lint check only; it did not authorize transition execution, historical-store
mutation, qualification, sizing, network, data, source integration, commit, or push.

Commands and results:

1. `.venv/bin/python -m pytest tests/acquisition/test_binance_usdm_harmonic_path_bound_transition.py -q --tb=short`
   - exit 1 in 2.9 seconds;
   - 53 cases failed and 16 passed.
2. `.venv/bin/python -m pytest tests/acquisition/test_binance_usdm_harmonic_path_bound_transition.py --collect-only -q`
   - exit 0 in 0.6 seconds;
   - 69 cases collected.
3. `.venv/bin/python -m pytest 'tests/acquisition/test_binance_usdm_harmonic_path_bound_transition.py::test_every_pinned_identity_mismatch_stops_before_any_mutation[lock]' -q --tb=short`
   - exit 0 in 0.8 seconds;
   - the representative rejection case passed in isolation.
4. `.venv/bin/python -m ruff check src/cryptofactors/acquisition/binance_usdm_harmonic_path_bound_transition.py scripts/research/apply_binance_usdm_harmonic_path_bound_transition.py tests/acquisition/test_binance_usdm_harmonic_path_bound_transition.py`
   - exit 1;
   - one `F401`: unused `os` import in the test module.

## Consolidated finding

The 53 pytest failures have one shared cause. The first literal-pin test executes
`importlib.reload(transition)`, which replaces the module's `TransitionError` class. The
file-level `TransitionError` import still points to the pre-reload class, so every later
`pytest.raises(TransitionError)` fails to catch the correct new-class exception. The same
representative case passes when run alone, proving the suite-order class-identity fault.

Ruff independently reports the unused top-level `os` import. No production or CLI defect
was exposed by this run.

## Spark test-only authority

Implementation Dev - Codex Spark is authorized to edit only
`tests/acquisition/test_binance_usdm_harmonic_path_bound_transition.py` and make exactly
these two mechanical changes:

1. remove the unused top-level `import os`;
2. in `test_pinned_review208_identities_are_literal`, remove `import importlib` and replace
   `fresh = importlib.reload(transition)` with `fresh = transition`.

No other line or path may change. Spark runs no test, linter, control, qualification,
transition, sizing, network, data, Git, commit, push, or repository-record command.
Return only the corrected test SHA-256 and unchanged count of 26 test functions, then
stop. The reviewer will rerun the focused suite and Ruff directly.

## Stop boundary

Hermes and transition execution remain unauthorized. No ordinary qualification, sizing
source change or retry, acquisition, normalization, catalog publication, NautilusTrader,
Harmonic Trader, payoff, PAPER, LIVE, paid-source, reduced-scope, or next-ticket work is
authorized. Gate 2 remains unaccepted and next ticket remains `NONE`.
