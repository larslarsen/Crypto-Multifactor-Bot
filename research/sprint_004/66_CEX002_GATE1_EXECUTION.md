# CEX-002 Gate 1 Execution Record

Date: 2026-08-18

Reviewer-authorized integration base: review 65 (`research/sprint_004/65_CEX002_CLAUDE_SOURCE_REVIEW.md`)
as revised for the intermediate Gate 1 integration, and the matching `CURRENT_TASK.md`
"Claude corrective source acceptance" section.

## 1. Pre-commit identity verification

The three reviewed Python paths match review 65 exactly:

- `src/cryptofactors/acquisition/binance_usdm_harmonic_qualification.py`
  `4f60ef74478796acb138a34f55ba9f5f9808cbcaff83f0f09310a6cb4a9593a1`
- `scripts/research/qualify_binance_usdm_harmonic_sources.py`
  `af3aca3cf461ce2cfd31dd8db5b4aa53a9c1e5332a7bc8a622f250a3bb2855f6`
- `tests/acquisition/test_binance_usdm_harmonic_qualification.py`
  `4ba04c535d81e9a6bac921b9b45844009f72694e48805fafd34a771a75e06abd`

All fixture hashes match review 63 exactly (unchanged in review 65).

## 2. Environmental evidence: in-place full suite

The unchanged in-place full suite (`pytest tests/`) fails only in preserved, unintegrated
DEX/BitMEX paths and was recorded as nonblocking environmental evidence under the
reviewer's revised intermediate-gate ruling. No `-k` substitute and no clean-worktree
rerun are required for this Gate 1 integration. The unchanged full suite remains mandatory
once at final CEX-002 release acceptance.

Observed failures (unchanged full selection):

1. `FAILED tests/acquisition/test_uniswap_v2.py::TestPairCreatedPilotEquivalence::test_existing_receipts_replay_identically_twice`
   — `AssertionError: expected 2120 receipts, got 3129` at `test_uniswap_v2.py:2041`.
2-6. `FAILED tests/acquisition/test_uniswap_v2_pair_events_v2_engine.py`:
   `test_production_attempt_atomic_success_and_lineage`,
   `test_production_journal_recovery_carries_authority_and_is_idempotent`,
   `test_production_startup_failure_replay_through_engine`,
   `test_production_startup_field_divergence_retains_journal[...]`,
   `test_production_cleanup_before_either_unlink`.

An additional committed-code hang was observed in
`tests/acquisition/test_uniswap_v2_pair_events_v2_matrix.py::test_live_lock_subprocess_contention_before_run_creation`
(exit 124). All of the above are outside the CEX-002 accepted source.

## 3. Authorized command sequence (intermediate Gate 1)

| # | Command | Exit | Result |
|---|---|---|---|
| 1 | `.venv/bin/python -m pytest tests/acquisition/test_binance_usdm_harmonic_qualification.py -q --tb=short` | 0 | 29 passed |
| 2 | `.venv/bin/python -m pytest tests/test_download_atomicity.py -q --tb=short` | 0 | 11 passed |
| 3 | `.venv/bin/python -m ruff check src/cryptofactors/ scripts/` | 0 | All checks passed |
| 4 | `python3 scripts/check_repo_control.py` | 0 | PASS |
| 5 | `git diff --check` | 0 | clean |

All five commands passed.

## 4. Real Gate 1 qualification / resume — EXECUTION FAILURE

### First run (report `/tmp/cex002_gate1_first.json`)

- Command:
  `/bin/bash -lc 'set -a; . ./.env; set +a; .venv/bin/python scripts/research/qualify_binance_usdm_harmonic_sources.py --store-root data/cex002_qualify --progress-path data/cex002_qualify/cex002_qualification_progress.json --report-path /tmp/cex002_gate1_first.json'`
- Exit code: 1 (execution failure — stops publication per review 65)
- Failure: transport connection error to Binance public data S3
  (`https://s3-ap-northeast-1.amazonaws.com/data.binance.vision`, list-type=2, prefix
  `data/futures/um/monthly/trades/CELRUSDT/`):
  `httpx.ConnectError: [Errno 104] Connection reset by peer`,
  raised as `source_audit.errors.DownloadError` from `_list_page` in
  `binance_usdm_harmonic_qualification.py:1265` via
  `source_audit/download.py:225`.
- Store/progress state before run: `data/cex002_qualify` did not exist (first run).
- Resumed report (`research/sprint_004/62_CEX002_GATE1_SOURCE_PROCUREMENT.json`):
  NOT RUN — blocked by first-run exit 1.
- Semantic resume-identity check: NOT RUN — blocked by first-run exit 1.

Per review 65, "Exit code 1 is an execution failure and stops publication." The second run,
resume-identity check, evidence recording, and commit/push are therefore halted.

## 5. Publication

NOT EXECUTED — blocked by the real qualification exit 1 per review 65. No network-derived
report, execution evidence, or commit was produced from this run.