# CEX-002 Migration Fixture Source Acceptance

**Date:** 2026-08-22
**Reviewer:** Lead Quantitative Finance Researcher/Engineer
**Decision:** `TEST_SOURCE_ACCEPTED_FOR_REINTEGRATION`
**Gate 1:** Source finding remains accepted; affected publication authority stays suspended
**Gate 2:** Not accepted

## Accepted correction

| Path | SHA-256 | Decision |
|---|---|---|
| `src/cryptofactors/acquisition/binance_usdm_harmonic_qualification.py` | `2f88ad6e7cfc531fefe3d9c7a9ddbc830741687e93c51450fc826062dffb2c74` | Committed, accepted, and frozen |
| `tests/acquisition/test_binance_usdm_harmonic_qualification.py` | `e4bd0203668a4488fe56ba4efede53696d908a0a68a227d005e3420badc29dea` | Accepted for reintegration |

The corrected test path contains exactly 315 `def test_` functions. The production path
is unchanged.

Claude added a narrowly scoped Kline-plus-funding index and made the existing accepted-v4
fixture accept an index factory while preserving its default for every other caller. The
failing migration test alone selects the new fixture. Its complete published-object
domain contains the intentionally colliding monthly/daily Kline basenames and genuinely
unique monthly funding-rate basenames. The test binds to that complete domain, explicitly
proves exact-singleton membership and retained lookup, removes only the proved row, and
then preserves the original record/flush and byte-identical checkpoint assertions through
the reviewed migration.

This closes review 205 without weakening ADR-0022 or changing production. The reviewer
performed read-only static inspection only and ran no test, linter, repository-control,
acceptance, qualification, sizing, network, or data-mutation command.

## Hermes reintegration authority

Jr Dev - Hermes is authorized to integrate only the accepted test path and publish the
result in:

- `research/sprint_004/207_CEX002_MIGRATION_FIXTURE_REINTEGRATION.md`;
- `docs/handoff/CURRENT_TASK.md`; and
- `tickets/CEX-002.md`.

Hermes must first verify both hashes above and `HEAD == origin/main` at the reviewer
publication commit. It must not stage, edit, delete, restore, or include any unrelated
dirty path. Run this stop-on-first-failure sequence:

1. `.venv/bin/python -m pytest tests/acquisition/test_binance_usdm_harmonic_qualification.py -q --tb=short`
2. `.venv/bin/python -m ruff check src/cryptofactors/acquisition/binance_usdm_harmonic_qualification.py tests/acquisition/test_binance_usdm_harmonic_qualification.py`
3. Publish record 207 and update the two control files for reviewer inspection.
4. `python3 scripts/check_repo_control.py`
5. `git diff --check -- tests/acquisition/test_binance_usdm_harmonic_qualification.py docs/handoff/CURRENT_TASK.md tickets/CEX-002.md research/sprint_004/207_CEX002_MIGRATION_FIXTURE_REINTEGRATION.md`

If pytest fails, skip Ruff. In either failure case, still perform steps 3-5 to validate
and preserve the stop record. Record each command verbatim with exit status, duration,
and key output; both final hashes; the reviewer publication identity used as the base;
and the exact intended staged path list. Set the next required actor to the reviewer in
every outcome. Commit and push only the four enumerated paths, establish
`HEAD == origin/main`, report the resulting commit and push result to the owner, and stop.

## Stop boundary

This reintegration does not authorize qualification execution, source-identity or
historical-store mutation, sizing retry, acquisition, normalization, catalog publication,
NautilusTrader, Harmonic Trader, payoff, PAPER, LIVE, paid-source, reduced-scope, full-suite,
or next-ticket work. Gate 2 remains unaccepted and next ticket remains `NONE`.
