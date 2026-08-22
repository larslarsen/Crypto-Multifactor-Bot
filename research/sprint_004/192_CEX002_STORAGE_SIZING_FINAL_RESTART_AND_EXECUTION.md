# CEX-002 Storage-Sizing Final Restart and Execution

Date: 2026-08-22
Actor: Jr Dev - Hermes
Ticket: CEX-002

## Scope

Review 191 authorized Hermes to integrate only Spark's final accepted one-file sizing-test
correction and run the stop-on-first-failure verification sequence. The focused tests
passed, but the second required command, exact-path ruff, exited nonzero. Per review 191,
Hermes stopped immediately.

No source repair, test repair, retry, substitution, repository-control command, sizing
invocation, second sizing invocation, network call, credential load, qualification, bulk
acquisition, normalization, catalog publication, Gate-2 acceptance, NautilusTrader work,
Harmonic Trader work, payoff analysis, PAPER, LIVE, paid-source, reduced-scope, or
next-ticket work was run.

## Preproof

`git rev-parse HEAD origin/main`

```text
e0bd59e41e4d9b1b10c6285f393f87d1faf7e872
e0bd59e41e4d9b1b10c6285f393f87d1faf7e872
```

Accepted path identities:

```text
795eab0312064e3d7be7dd8f826b5dc5754a8e6b5e702872ac3699dad1532390  src/cryptofactors/acquisition/binance_usdm_harmonic_sizing.py
78ee687c734fc94070952d290752acdbd007970fb26c616e5e6845f1de3702ad  scripts/research/size_binance_usdm_harmonic_release.py
585f20db0461ad92af7cf6b1d4143aa52c4dfdff5f2bbfa44e76d4f6334e9f96  tests/acquisition/test_binance_usdm_harmonic_sizing.py
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
sizing_outputs_absent
```

## Command evidence

### C1 - focused sizing tests

Command:

```bash
.venv/bin/python -m pytest tests/acquisition/test_binance_usdm_harmonic_sizing.py -q --tb=short
```

Result:

```text
........................................................................ [ 97%]
..                                                                       [100%]
elapsed_seconds=2
exit_status=0
```

### C2 - exact-path ruff

Command:

```bash
.venv/bin/python -m ruff check src/cryptofactors/acquisition/binance_usdm_harmonic_sizing.py scripts/research/size_binance_usdm_harmonic_release.py tests/acquisition/test_binance_usdm_harmonic_sizing.py
```

Result:

```text
exit_status=1
elapsed_seconds=1
```

Material transcript:

```text
F401 [*] `cryptofactors.acquisition.binance_usdm_harmonic_sizing.SIZING_ROW_BATCH` imported but unused
  --> tests/acquisition/test_binance_usdm_harmonic_sizing.py:36:5

F401 [*] `cryptofactors.acquisition.binance_usdm_harmonic_sizing.family_coefficients` imported but unused
  --> tests/acquisition/test_binance_usdm_harmonic_sizing.py:48:5

F401 [*] `cryptofactors.acquisition.binance_usdm_harmonic_sizing.verify_retained_sample` imported but unused
  --> tests/acquisition/test_binance_usdm_harmonic_sizing.py:64:5

Found 3 errors.
[*] 3 fixable with the `--fix` option.
```

Since C2 exited nonzero, all later review-191 commands were stopped:

- C3 `python3 scripts/check_repo_control.py` was not run.
- First sizing invocation was not run.
- Second sizing invocation was not run.

## Post-stop proof

The accepted three sizing paths remained at review-191 identities:

```text
795eab0312064e3d7be7dd8f826b5dc5754a8e6b5e702872ac3699dad1532390  src/cryptofactors/acquisition/binance_usdm_harmonic_sizing.py
78ee687c734fc94070952d290752acdbd007970fb26c616e5e6845f1de3702ad  scripts/research/size_binance_usdm_harmonic_release.py
585f20db0461ad92af7cf6b1d4143aa52c4dfdff5f2bbfa44e76d4f6334e9f96  tests/acquisition/test_binance_usdm_harmonic_sizing.py
```

The test path still contains exactly 44 `def test_` functions.

The sizing outputs remained absent:

```text
sizing_outputs_absent
```

No sizing receipt, content-addressed sizing envelope, partial sizing file, capacity field,
or fixed-target reproof artifact was created.

## Git scope

Intended staged paths for this publication are exactly:

- `tests/acquisition/test_binance_usdm_harmonic_sizing.py`
- `research/sprint_004/192_CEX002_STORAGE_SIZING_FINAL_RESTART_AND_EXECUTION.md`
- `docs/handoff/CURRENT_TASK.md`
- `tickets/CEX-002.md`

No unrelated dirty path, data/evidence path, database sidecar, DEX path, BitMEX path,
catalog/ingest path, fixture path, receipt 180, or sizing envelope is staged by this
record.

## Disposition

The review-191 restart stopped at the exact-path ruff command. Gate 1 remains accepted.
Gate 2 remains unaccepted. The real sizing receipt was not created. Next ticket remains
`NONE`.

Next required actor: Lead Quantitative Finance Researcher/Engineer - inspect record 192.
