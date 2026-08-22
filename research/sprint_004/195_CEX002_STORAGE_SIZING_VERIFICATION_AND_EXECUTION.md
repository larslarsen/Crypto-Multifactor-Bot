# CEX-002 Storage-Sizing Verification and Execution

Date: 2026-08-22
Actor: Jr Dev - Hermes
Ticket: CEX-002

## Scope

Review 194 authorized Hermes to integrate only Claude's accepted three-import sizing-test
cleanup, run focused tests, exact-path Ruff, repository control, and then conditionally run
exactly two local sizing invocations. The three verification commands passed. The first
authorized sizing invocation exited nonzero, so Hermes stopped immediately and did not run
the second sizing invocation.

No source repair, test repair, retry, substitution, second sizing invocation, network call,
credential load, qualification, bulk acquisition, normalization, catalog publication,
Gate-2 acceptance, NautilusTrader work, Harmonic Trader work, payoff analysis, PAPER, LIVE,
paid-source, reduced-scope, or next-ticket work was run.

## Preproof

`git rev-parse HEAD origin/main`

```text
bec5495f78f36c3769e10397244ff3660b19f668
bec5495f78f36c3769e10397244ff3660b19f668
```

Accepted path identities:

```text
795eab0312064e3d7be7dd8f826b5dc5754a8e6b5e702872ac3699dad1532390  src/cryptofactors/acquisition/binance_usdm_harmonic_sizing.py
78ee687c734fc94070952d290752acdbd007970fb26c616e5e6845f1de3702ad  scripts/research/size_binance_usdm_harmonic_release.py
fda45c767e8cf271136f2a25769e37f64c57428fde15e508d0045b975679b2c7  tests/acquisition/test_binance_usdm_harmonic_sizing.py
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

The following outputs were absent before execution:

```text
sizing_outputs_absent
```

The integrated accepted test diff was exactly the three deleted unused imports:

- `SIZING_ROW_BATCH`
- `family_coefficients`
- `verify_retained_sample`

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

### C2 - exact-path Ruff

Command:

```bash
.venv/bin/python -m ruff check src/cryptofactors/acquisition/binance_usdm_harmonic_sizing.py scripts/research/size_binance_usdm_harmonic_release.py tests/acquisition/test_binance_usdm_harmonic_sizing.py
```

Result:

```text
All checks passed!
elapsed_seconds=0
exit_status=0
```

### C3 - repository control

Command:

```bash
python3 scripts/check_repo_control.py
```

Result:

```text
Repo control check: PASS
elapsed_seconds=1
exit_status=0
```

### S1 - first local sizing invocation

Command:

```bash
.venv/bin/python scripts/research/size_binance_usdm_harmonic_release.py --manifest-detail-path data/cex002_qualify/evidence/manifests/sha256/1d21de4d68fb0dfd330dc480a0d27ddf2216c3b7d5e93b13ff70ea26230f968d.jsonl.gz
```

Result:

```text
ERROR: accepted sizing authority does not match its pinned identity
elapsed_seconds=167
exit_status=1
```

Since S1 exited nonzero, the second sizing invocation was not run.

## Post-stop proof

The accepted three sizing paths remained at review-194 identities:

```text
795eab0312064e3d7be7dd8f826b5dc5754a8e6b5e702872ac3699dad1532390  src/cryptofactors/acquisition/binance_usdm_harmonic_sizing.py
78ee687c734fc94070952d290752acdbd007970fb26c616e5e6845f1de3702ad  scripts/research/size_binance_usdm_harmonic_release.py
fda45c767e8cf271136f2a25769e37f64c57428fde15e508d0045b975679b2c7  tests/acquisition/test_binance_usdm_harmonic_sizing.py
```

The test path still contains exactly 44 `def test_` functions.

The sizing outputs remained absent:

```text
sizing_outputs_absent
```

The post-stop process check matched only the check command itself; no independent sizing
process was running.

No sizing receipt, content-addressed sizing envelope, partial sizing file, capacity field,
or fixed-target reproof artifact was created.

## Git scope

Intended staged paths for this publication are exactly:

- `tests/acquisition/test_binance_usdm_harmonic_sizing.py`
- `research/sprint_004/195_CEX002_STORAGE_SIZING_VERIFICATION_AND_EXECUTION.md`
- `docs/handoff/CURRENT_TASK.md`
- `tickets/CEX-002.md`

No unrelated dirty path, data/evidence path, database sidecar, DEX path, BitMEX path,
catalog/ingest path, fixture path, receipt 180, or sizing envelope is staged by this
record.

## Disposition

The review-194 restart stopped at the first local sizing invocation. Gate 1 remains
accepted. Gate 2 remains unaccepted. The real sizing receipt was not created. Next ticket
remains `NONE`.

Next required actor: Lead Quantitative Finance Researcher/Engineer - inspect record 195.
