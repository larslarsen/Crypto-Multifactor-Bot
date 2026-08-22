# CEX-002 Storage-Sizing Integration and Execution

Date: 2026-08-22
Actor: Jr Dev - Hermes
Ticket: CEX-002

## Scope

Review 184 authorized integration of exactly three accepted sizing paths, then a
stop-on-first-failure command sequence. The first command, the focused sizing test file,
exited nonzero. Per review 184, Hermes stopped immediately.

No ruff command, repository-control command in the review-184 sequence, sizing invocation,
second sizing invocation, network call, credential load, qualification, bulk acquisition,
normalization, catalog publication, Gate-2 acceptance, NautilusTrader work, Harmonic
Trader work, payoff analysis, PAPER, LIVE, paid-source, reduced-scope, or next-ticket work
was run.

## Preproof

`git rev-parse HEAD origin/main`

```text
775e5a32921a22ab359184d50372a964c4070511
775e5a32921a22ab359184d50372a964c4070511
```

Accepted path identities:

```text
795eab0312064e3d7be7dd8f826b5dc5754a8e6b5e702872ac3699dad1532390  src/cryptofactors/acquisition/binance_usdm_harmonic_sizing.py
78ee687c734fc94070952d290752acdbd007970fb26c616e5e6845f1de3702ad  scripts/research/size_binance_usdm_harmonic_release.py
e7127f9724ce046233979ec29d43035ff5358c213beee2b9cd22b0e841ee323a  tests/acquisition/test_binance_usdm_harmonic_sizing.py
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
elapsed_seconds=3
```

Material transcript:

```text
.EEEEEEEEEEEEE............F.FFFFFFFF.EEEEE.FFEEEEEEEEEEEEE..EEEEEE..FFFF [ 97%]
.F                                                                       [100%]
```

Primary collection/setup error:

```text
TypeError: open() got an unexpected keyword argument 'mtime'
```

This occurred at:

```text
tests/acquisition/test_binance_usdm_harmonic_sizing.py:196
with gzip.open(detail_path, "wb", compresslevel=9, mtime=0) as handle:
```

Additional material failures reported by pytest included:

- `test_headed_input_is_measured_as_headed` failed with
  `SizingError: the retained sample header form disagrees with its checkpoint`.
- The corrupt-archive parameterized cases raised `SizingError` directly for invalid ZIP,
  empty member, escaping path, absolute path, non-CSV member, schema-width mismatch, and
  non-decodable CSV.
- `test_rational_comparison_uses_cross_multiplication_beyond_float_precision` raised
  `SizingError: sizing component is not a positive integer`.
- `test_catalog_reserve_and_publication_contracts` raised
  `SizingError: sizing component is not a positive integer`.
- Receipt/envelope publication tests raised `SizingError` for differing existing targets,
  symlink refusal, escaping envelope path, and no-follow symlink reads.

Pytest summary reported 16 failed tests and 37 errors. Since C1 exited nonzero, all later
review-184 commands were stopped:

- C2 ruff was not run.
- C3 `python3 scripts/check_repo_control.py` in the review-184 sequence was not run.
- First sizing invocation was not run.
- Second sizing invocation was not run.

## Post-stop proof

The accepted three sizing paths still match review 184:

```text
795eab0312064e3d7be7dd8f826b5dc5754a8e6b5e702872ac3699dad1532390  src/cryptofactors/acquisition/binance_usdm_harmonic_sizing.py
78ee687c734fc94070952d290752acdbd007970fb26c616e5e6845f1de3702ad  scripts/research/size_binance_usdm_harmonic_release.py
e7127f9724ce046233979ec29d43035ff5358c213beee2b9cd22b0e841ee323a  tests/acquisition/test_binance_usdm_harmonic_sizing.py
```

The sizing outputs remained absent:

```text
research/sprint_004/180_CEX002_GATE2_STORAGE_SIZING.json
data/cex002_qualify/evidence/sizing/v1/envelopes/sha256
```

## Git scope

Intended staged paths for this publication are exactly:

- `src/cryptofactors/acquisition/binance_usdm_harmonic_sizing.py`
- `scripts/research/size_binance_usdm_harmonic_release.py`
- `tests/acquisition/test_binance_usdm_harmonic_sizing.py`
- `research/sprint_004/185_CEX002_STORAGE_SIZING_INTEGRATION_AND_EXECUTION.md`
- `docs/handoff/CURRENT_TASK.md`
- `tickets/CEX-002.md`

No unrelated dirty path, data/evidence path, database sidecar, DEX path, BitMEX path,
catalog/ingest path, or fixture path is staged by this record.

## Disposition

The review-184 integration stopped at the focused sizing test command. Gate 1 remains
accepted. Gate 2 remains unaccepted. The real sizing receipt was not created. Next ticket
remains `NONE`.

Next required actor: Lead Quantitative Finance Researcher/Engineer - inspect record 185.
