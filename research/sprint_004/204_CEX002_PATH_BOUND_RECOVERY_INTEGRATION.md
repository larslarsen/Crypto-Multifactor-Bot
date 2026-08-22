# CEX-002 Path-Bound Recovery Integration

Date: 2026-08-22
Actor: Jr Dev - Hermes
Ticket: CEX-002

## Scope

Review 203 authorized Hermes to integrate exactly two ADR-0022 qualification files, run
the stop-on-first-failure sequence, publish this record, update the two control files, and
stop for reviewer inspection. The first required command, the qualification-module test
suite, exited nonzero. Per review 203, Hermes skipped exact-path Ruff but still published
the stop record and control-plane transition.

No qualification execution, authority mutation, sizing retry, acquisition, normalization,
catalog publication, NautilusTrader work, Harmonic Trader work, payoff analysis, PAPER,
LIVE, paid-source, reduced-scope, or next-ticket work was run.

## Preproof

`git rev-parse HEAD origin/main`

```text
4b79a71fad9dfd608535ae8a72ba74cd4b85c018
4b79a71fad9dfd608535ae8a72ba74cd4b85c018
```

Accepted path identities:

```text
2f88ad6e7cfc531fefe3d9c7a9ddbc830741687e93c51450fc826062dffb2c74  src/cryptofactors/acquisition/binance_usdm_harmonic_qualification.py
0f9086db07fb0a4024135a7f07370d9cf9a98beca8bd20a8a829f322153fb867  tests/acquisition/test_binance_usdm_harmonic_qualification.py
```

`rg -c '^def test_' tests/acquisition/test_binance_usdm_harmonic_qualification.py`

```text
315
```

The integrated source/test diff was confined to the two paths accepted by review 203.

## Command evidence

### C1 - qualification-module tests

Command:

```bash
.venv/bin/python -m pytest tests/acquisition/test_binance_usdm_harmonic_qualification.py -q --tb=short
```

Result:

```text
........................................................................ [ 17%]
........................................................................ [ 34%]
........................................................................ [ 51%]
........................................................................ [ 68%]
........................................................................ [ 86%]
................F.........................................               [100%]
```

Failure:

```text
FAILED tests/acquisition/test_binance_usdm_harmonic_qualification.py::test_migration_does_not_adopt_a_recoverable_missing_checkpoint_entry
tests/acquisition/test_binance_usdm_harmonic_qualification.py:9339: in test_migration_does_not_adopt_a_recoverable_missing_checkpoint_entry
    key = next(
E   StopIteration
```

Exit:

```text
elapsed_seconds=7
exit_status=1
```

Since C1 exited nonzero, exact-path Ruff was skipped per the review-203 stop rule.

### C2 - exact-path Ruff

Not run because C1 failed.

## Post-stop proof

The accepted two ADR-0022 paths remained at review-203 identities:

```text
2f88ad6e7cfc531fefe3d9c7a9ddbc830741687e93c51450fc826062dffb2c74  src/cryptofactors/acquisition/binance_usdm_harmonic_qualification.py
0f9086db07fb0a4024135a7f07370d9cf9a98beca8bd20a8a829f322153fb867  tests/acquisition/test_binance_usdm_harmonic_qualification.py
```

The test path still contains exactly 315 `def test_` functions.

## Repository-control and whitespace validation

Per review 203, these commands are run after publishing this record and updating the two
control files:

```bash
python3 scripts/check_repo_control.py
git diff --check -- src/cryptofactors/acquisition/binance_usdm_harmonic_qualification.py tests/acquisition/test_binance_usdm_harmonic_qualification.py docs/handoff/CURRENT_TASK.md tickets/CEX-002.md research/sprint_004/204_CEX002_PATH_BOUND_RECOVERY_INTEGRATION.md
```

Their exact results are recorded in the final committed state after execution.

Results:

```text
Repo control check: PASS
elapsed_seconds=0
exit_status=0
```

```text
elapsed_seconds=0
exit_status=0
```

## Git scope

Intended staged paths for this publication are exactly:

- `src/cryptofactors/acquisition/binance_usdm_harmonic_qualification.py`
- `tests/acquisition/test_binance_usdm_harmonic_qualification.py`
- `research/sprint_004/204_CEX002_PATH_BOUND_RECOVERY_INTEGRATION.md`
- `docs/handoff/CURRENT_TASK.md`
- `tickets/CEX-002.md`

No unrelated dirty path, data/evidence path, database sidecar, DEX path, BitMEX path,
catalog/ingest path, sizing receipt, or sizing envelope is staged by this record.

## Disposition

The review-203 integration stopped at the qualification-module test command. Gate 2
remains unaccepted. Next ticket remains `NONE`.

Next required actor: Lead Quantitative Finance Researcher/Engineer - inspect record 204.
