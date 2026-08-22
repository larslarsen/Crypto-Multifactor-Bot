# CEX-002 Path-Bound Source and Test Acceptance

**Date:** 2026-08-22
**Reviewer:** Lead Quantitative Finance Researcher/Engineer
**Decision:** `SOURCE_AND_TEST_ACCEPTED_FOR_INTEGRATION`
**Gate 1:** Source finding remains accepted; affected publication authority stays suspended
**Gate 2:** Not accepted

## Accepted drop

| Path | SHA-256 |
|---|---|
| `src/cryptofactors/acquisition/binance_usdm_harmonic_qualification.py` | `2f88ad6e7cfc531fefe3d9c7a9ddbc830741687e93c51450fc826062dffb2c74` |
| `tests/acquisition/test_binance_usdm_harmonic_qualification.py` | `0f9086db07fb0a4024135a7f07370d9cf9a98beca8bd20a8a829f322153fb867` |

The accepted test path contains 315 `def test_` functions. Production remained
byte-identical throughout the review-201/review-202 test-only corrections.

The final test proves a genuinely basename-unique funding-rate recovery against the
complete fixture domain, exact object and sidecar identities, one exact retained-byte
total at lock time, and immediate-rerun identity. The no-write fixture independently
constructs a valid uncheckpointed recovery and a reconcilable reservation while the
installed plan requires rejected lineage, then proves neither mutation path executes.

Together with the accepted prior tests and source, the drop implements ADR-0022's
exact-singleton path binding, preserves rejected legacy lineage, excludes it from every
effective authority consumer, fails an executing plan before durable mutation, and
separates retained logical keys, unique objects, and unique bytes.

The reviewer ran no test, linter, repository-control, acceptance, qualification, sizing,
network, or data-mutation command. Hermes owns command evidence.

## Hermes integration authority

Jr Dev - Hermes is authorized to integrate only the two exact accepted files above and
publish the integration result in:

- `research/sprint_004/204_CEX002_PATH_BOUND_RECOVERY_INTEGRATION.md`;
- `docs/handoff/CURRENT_TASK.md`; and
- `tickets/CEX-002.md`.

Hermes must first verify both accepted hashes and `HEAD == origin/main` at the reviewer
publication commit. It must not stage, edit, delete, restore, or include any unrelated
dirty path.

Run this stop-on-first-failure sequence:

1. `.venv/bin/python -m pytest tests/acquisition/test_binance_usdm_harmonic_qualification.py -q --tb=short`
2. `.venv/bin/python -m ruff check src/cryptofactors/acquisition/binance_usdm_harmonic_qualification.py tests/acquisition/test_binance_usdm_harmonic_qualification.py`
3. Publish record 204 and update the two control files for reviewer inspection.
4. `python3 scripts/check_repo_control.py`
5. `git diff --check -- src/cryptofactors/acquisition/binance_usdm_harmonic_qualification.py tests/acquisition/test_binance_usdm_harmonic_qualification.py docs/handoff/CURRENT_TASK.md tickets/CEX-002.md research/sprint_004/204_CEX002_PATH_BOUND_RECOVERY_INTEGRATION.md`

Record every command verbatim with exit status, duration, key output, the final hashes,
the exact staged/committed path list, commit identity, push result, and final
`HEAD == origin/main`. If pytest or Ruff fails, skip the other acceptance work but still
perform steps 3-5 to validate and preserve the stop record. Set the next required actor
to the reviewer for record-204 inspection in every outcome. Commit and push only the five
enumerated paths.

## Stop boundary

This integration does not authorize qualification execution, source-identity mutation,
sizing retry, acquisition, normalization, catalog publication, NautilusTrader, Harmonic
Trader, payoff, PAPER, LIVE, paid-source, reduced-scope, or next-ticket work. The
accepted historical store remains bound to its prior executing source identity; the
reviewer must decide the next authority transition after inspecting record 204. Gate 2
remains unaccepted and next ticket remains `NONE`.
