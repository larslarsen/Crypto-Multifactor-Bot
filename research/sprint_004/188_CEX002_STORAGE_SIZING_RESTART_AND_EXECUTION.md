# CEX-002 Storage-Sizing Restart and Execution

Date: 2026-08-22
Actor: Jr Dev - Hermes
Ticket: CEX-002

## Scope

Review 187 authorized Hermes to integrate only Spark's accepted one-file sizing-test
correction and restart review 184's stop-on-first-failure sequence. The first required
command, the focused sizing test file, exited nonzero. Per review 187, Hermes stopped
immediately.

No source repair, test repair, retry, substitution, ruff command, repository-control command
in the review-187 sequence, sizing invocation, second sizing invocation, network call,
credential load, qualification, bulk acquisition, normalization, catalog publication,
Gate-2 acceptance, NautilusTrader work, Harmonic Trader work, payoff analysis, PAPER, LIVE,
paid-source, reduced-scope, or next-ticket work was run.

## Preproof

`git rev-parse HEAD origin/main`

```text
c837dc679a8d0f94a88f2f66571a51d95b07dfe6
c837dc679a8d0f94a88f2f66571a51d95b07dfe6
```

Accepted path identities:

```text
795eab0312064e3d7be7dd8f826b5dc5754a8e6b5e702872ac3699dad1532390  src/cryptofactors/acquisition/binance_usdm_harmonic_sizing.py
78ee687c734fc94070952d290752acdbd007970fb26c616e5e6845f1de3702ad  scripts/research/size_binance_usdm_harmonic_release.py
e7b7103cb36f83642762a91101be98ae368ba41b425f8a3e00711632895da6de  tests/acquisition/test_binance_usdm_harmonic_sizing.py
```

`rg -c '^def test_' tests/acquisition/test_binance_usdm_harmonic_sizing.py`

```text
44
```

Accepted manifest detail:

```text
11294610 data/cex002_qualify/evidence/manifests/sha256/1d21de4d68fb0dfd330dc480a0d27ddf2216c3b7d5e93b13ff70ea26230f968d.jsonl.gz
576b3d7b03ff16fd492c5a9382e35f65e54d73ef3996c3a7fe5c6e6ba49b0fb4  data/cex002_qualify/evidence/manifests/sha256/1d21de4d68fb0dfd330dc480a0d27ddf2216c3b7d5e93b13ff70ea26230f968d.jsonl.gz
```

The following outputs were absent before test execution:

```text
research/sprint_004/180_CEX002_GATE2_STORAGE_SIZING.json
data/cex002_qualify/evidence/sizing/v1/envelopes/sha256
```

The sizing-process check matched only the check command itself; no independent sizing
process was running.

## Command evidence

### C1 - focused sizing tests

Command:

```bash
.venv/bin/python -m pytest tests/acquisition/test_binance_usdm_harmonic_sizing.py -q --tb=short
```

Result:

```text
exit_status=1
elapsed_seconds=2
```

Material transcript:

```text
............F......................F.........FFFFFFFFFFFFF..FF........F. [ 97%]
..                                                                       [100%]
```

Primary repeated failure:

```text
cryptofactors.acquisition.binance_usdm_harmonic_sizing.SizingError:
the cohort does not cover every physical family
context={
  'plan_entries': 14,
  'missing': [
    'daily/premiumIndexKlines',
    'daily/markPriceKlines',
    'daily/indexPriceKlines',
    'monthly/klines',
    'monthly/fundingRate',
    'monthly/premiumIndexKlines',
    'monthly/markPriceKlines',
    'monthly/indexPriceKlines',
    'daily/bookDepth'
  ]
}
```

Additional material failures reported by pytest included:

- `test_rational_comparison_uses_cross_multiplication_beyond_float_precision` rejected a
  path expression containing `Path(sample_dir) / digest` while scanning for ordinary
  division.
- `test_a_foreign_receipt_at_the_fixed_target_is_never_overwritten` expected
  `already occupies` but received the cohort-coverage `SizingError` first.
- `test_publication_refuses_a_symlink_swapped_after_the_check` expected
  `not a regular file` but received `a sizing envelope escapes its evidence root`.

Pytest summary reported 18 failed tests. Since C1 exited nonzero, all later review-187
commands were stopped:

- C2 ruff was not run.
- C3 `python3 scripts/check_repo_control.py` in the review-187 sequence was not run.
- First sizing invocation was not run.
- Second sizing invocation was not run.

## Post-stop proof

The sizing outputs remained absent:

```text
sizing_outputs_absent
```

The accepted three sizing paths remained the only intended implementation scope for this
restart. No sizing receipt, content-addressed sizing envelope, partial sizing file, or
fixed-target reproof artifact was created.

## Git scope

Intended staged paths for this publication are exactly:

- `tests/acquisition/test_binance_usdm_harmonic_sizing.py`
- `research/sprint_004/188_CEX002_STORAGE_SIZING_RESTART_AND_EXECUTION.md`
- `docs/handoff/CURRENT_TASK.md`
- `tickets/CEX-002.md`

No unrelated dirty path, data/evidence path, database sidecar, DEX path, BitMEX path,
catalog/ingest path, fixture path, receipt 180, or sizing envelope is staged by this
record.

## Disposition

The review-187 restart stopped at the focused sizing test command. Gate 1 remains
accepted. Gate 2 remains unaccepted. The real sizing receipt was not created. Next ticket
remains `NONE`.

Next required actor: Lead Quantitative Finance Researcher/Engineer - inspect record 188.
