# CEX-002 Migration Fixture Reintegration

Date: 2026-08-22
Actor: Jr Dev - Hermes
Ticket: CEX-002

## Scope

Review 206 authorized Hermes to integrate exactly one corrected qualification test file,
run the qualification-module tests, exact-path Ruff, repository control, restricted
whitespace validation, publish this record, update the two control files, commit and push
only the four enumerated paths, and stop for reviewer inspection.

No qualification execution, authority or historical-store mutation, sizing retry,
acquisition, normalization, catalog publication, NautilusTrader work, Harmonic Trader
work, payoff analysis, PAPER, LIVE, paid-source, reduced-scope, full-suite, or next-ticket
work was run.

## Preproof

`git rev-parse HEAD origin/main`

```text
ca4dd156f557f789b2a92a24ce866220d7451ab5
ca4dd156f557f789b2a92a24ce866220d7451ab5
```

Accepted path identities:

```text
2f88ad6e7cfc531fefe3d9c7a9ddbc830741687e93c51450fc826062dffb2c74  src/cryptofactors/acquisition/binance_usdm_harmonic_qualification.py
e4bd0203668a4488fe56ba4efede53696d908a0a68a227d005e3420badc29dea  tests/acquisition/test_binance_usdm_harmonic_qualification.py
```

`rg -c '^def test_' tests/acquisition/test_binance_usdm_harmonic_qualification.py`

```text
315
```

The visible integration diff was confined to
`tests/acquisition/test_binance_usdm_harmonic_qualification.py`.

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
..........................................................               [100%]
elapsed_seconds=7
exit_status=0
```

### C2 - exact-path Ruff

Command:

```bash
.venv/bin/python -m ruff check src/cryptofactors/acquisition/binance_usdm_harmonic_qualification.py tests/acquisition/test_binance_usdm_harmonic_qualification.py
```

Result:

```text
All checks passed!
elapsed_seconds=0
exit_status=0
```

## Repository-control and whitespace validation

Per review 206, these commands are run after publishing this record and updating the two
control files:

```bash
python3 scripts/check_repo_control.py
git diff --check -- tests/acquisition/test_binance_usdm_harmonic_qualification.py docs/handoff/CURRENT_TASK.md tickets/CEX-002.md research/sprint_004/207_CEX002_MIGRATION_FIXTURE_REINTEGRATION.md
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

- `tests/acquisition/test_binance_usdm_harmonic_qualification.py`
- `research/sprint_004/207_CEX002_MIGRATION_FIXTURE_REINTEGRATION.md`
- `docs/handoff/CURRENT_TASK.md`
- `tickets/CEX-002.md`

No unrelated dirty path, production source path, data/evidence path, database sidecar, DEX
path, BitMEX path, catalog/ingest path, sizing receipt, or sizing envelope is staged by
this record.

## Disposition

The review-206 reintegration passed qualification-module tests and exact-path Ruff. Gate 2
remains unaccepted. Next ticket remains `NONE`.

Next required actor: Lead Quantitative Finance Researcher/Engineer - inspect record 207.
