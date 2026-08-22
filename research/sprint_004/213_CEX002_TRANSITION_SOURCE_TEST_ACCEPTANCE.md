# CEX-002 Transition Source and Test Acceptance

**Date:** 2026-08-22
**Reviewer:** Lead Quantitative Finance Researcher/Engineer
**Decision:** `SOURCE_AND_TEST_ACCEPTED_FOR_INTEGRATION`
**Architecture:** ADR-0022 and reviews 208-212 remain controlling
**Gate 1:** Source finding remains accepted; affected publication authority stays suspended
**Gate 2:** Not accepted

## Accepted drop

| Path | SHA-256 |
|---|---|
| `src/cryptofactors/acquisition/binance_usdm_harmonic_path_bound_transition.py` | `f9a1bc89c63b22c974d020044ea8732939358efae00b42f2141bfd0eee34e5e5` |
| `scripts/research/apply_binance_usdm_harmonic_path_bound_transition.py` | `ada238d22560ddcaf834dff03d0da44c546856090e6133cf5afeb7be3d50aabd` |
| `tests/acquisition/test_binance_usdm_harmonic_path_bound_transition.py` | `60b018f05e5d96e0863c529ca6670e6563c9c3cead9539b30dbf381803ab76ff` |

The test path contains 26 `def test_` functions and collects 69 cases. The accepted
qualification source and 315-test path remain byte-identical at `2f88ad6e...` and
`e4bd0203...` respectively.

The reviewer completed a full static pass across the transition production, tests, and
standalone CLI. Under the owner's explicit authorization, the reviewer also corrected
the mechanical test-harness defects, reran the complete focused suite, and ran exact-path
Ruff. This avoided another developer/test-integration feedback cycle.

## Validation evidence

1. `.venv/bin/python -m pytest tests/acquisition/test_binance_usdm_harmonic_path_bound_transition.py -q --tb=short`
   - exit 0;
   - all 69 collected cases passed.
2. `.venv/bin/python -m ruff check src/cryptofactors/acquisition/binance_usdm_harmonic_path_bound_transition.py scripts/research/apply_binance_usdm_harmonic_path_bound_transition.py tests/acquisition/test_binance_usdm_harmonic_path_bound_transition.py`
   - exit 0;
   - `All checks passed!`
3. `git diff --check -- src/cryptofactors/acquisition/binance_usdm_harmonic_path_bound_transition.py scripts/research/apply_binance_usdm_harmonic_path_bound_transition.py tests/acquisition/test_binance_usdm_harmonic_path_bound_transition.py`
   - exit 0.

No historical-store transition, qualification, sizing, network, acquisition, data
mutation, repository-control, commit, or source-integration command was run.

## Acceptance rationale

The accepted transition is pinned to the exact review-208 historical state and target
source identity. It proves both compressed and streamed uncompressed manifest identities,
preserves all four prior evidence objects before authority mutation, and permits only the
fresh, ledger-advanced/lock-pending, and complete states. Advanced states require and
rehash all four evidence objects. The ledger changes only by one exact target receipt and
recomputed integrity; the lock changes only by the target code/config identity, proved
ledger binding, and explicit non-download transition metadata.

The transaction is receipt-first and lock-last, resumes its one exact middle state without
a duplicate receipt, is byte-for-byte idempotent after completion, rejects every other
mixed or widened state, and exposes no network, credential, acquisition, reconciliation,
policy-override, or authority-override path.

## Hermes integration authority

Jr Dev - Hermes is authorized to integrate only the three exact accepted paths above and
publish the integration result in:

- `research/sprint_004/214_CEX002_TRANSITION_INTEGRATION.md`;
- `docs/handoff/CURRENT_TASK.md`; and
- `tickets/CEX-002.md`.

Hermes must first verify all three accepted hashes and `HEAD == origin/main` at the
review-213 publication commit. It must not edit the accepted source, script, or test, and
must not stage, restore, delete, or include any unrelated dirty path. The reviewer already
owns the focused pytest and Ruff evidence; Hermes must not rerun either command.

Hermes must publish record 214, set the next required actor to the reviewer, run
`python3 scripts/check_repo_control.py`, and run:

`git diff --check -- src/cryptofactors/acquisition/binance_usdm_harmonic_path_bound_transition.py scripts/research/apply_binance_usdm_harmonic_path_bound_transition.py tests/acquisition/test_binance_usdm_harmonic_path_bound_transition.py docs/handoff/CURRENT_TASK.md tickets/CEX-002.md research/sprint_004/214_CEX002_TRANSITION_INTEGRATION.md`

Record the accepted identities, reviewer validation evidence, repository-control and
whitespace results, exact staged path list, commit identity, push result, and final
`HEAD == origin/main`. Commit and push only those six enumerated paths, then stop.

## Stop boundary

Integration does not authorize the historical-store transition, ordinary qualification,
sizing source change or retry, acquisition, normalization, catalog publication,
NautilusTrader, Harmonic Trader, payoff, PAPER, LIVE, paid-source, reduced-scope, or
next-ticket work. Gate 2 remains unaccepted and next ticket remains `NONE`.
