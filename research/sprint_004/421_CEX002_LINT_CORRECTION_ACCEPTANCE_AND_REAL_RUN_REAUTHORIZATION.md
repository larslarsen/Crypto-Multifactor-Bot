# CEX-002 Review 421 — Lint Correction Acceptance and Real-Run Reauthorization

- **Date:** 2026-09-01
- **Reviewer:** Lead Quantitative Finance Researcher/Engineer
- **Ticket:** CEX-002
- **Decision:** accept the function-scoped correction; reauthorize integration and one real production run
- **Gate 2:** `ACCEPTED`
- **Gate 3:** `IN_PROGRESS`
- **Next required actor:** Jr Dev — Hermes
- **Next ticket:** `NONE`

## Accepted unintegrated source drop

Static inspection accepts Review 420's exact two function-scoped test edits. The required `key`
assignment is restored immediately before `payload` in
`test_unsafe_zip_member_paths_are_rejected`; the unused copy is absent between the `BytesIO`
import and `target` in `test_symlink_and_multi_member_zips_are_rejected`. Sol's sole authorized
ruff command exited 0 with complete output `All checks passed!`.

The accepted unintegrated identities are:

| Path | Lines | SHA-256 |
|---|---:|---|
| `src/cryptofactors/ingest/binance_usdm_open_interest.py` | 1,432 | `c2b8835445036359e870cb6a3fa77907bc9ec766a2e1da355ef837e7c22a70d8` |
| `scripts/research/normalize_binance_usdm_open_interest.py` | 53 | `33585315bb061a97d68197792ba86d8911383534d28c734f73f946900464a675` |
| `tests/ingest/test_binance_usdm_open_interest.py` | 439 | `4c6d796ee1e7ec8e1b5b0b2ffe1ac1ad581aee6777e661401e086cc02ac9f8b5` |

The production source and CLI are byte-identical to Review 417. This review supersedes Review
417 only for the accepted test identity, terminal record number, runner-directory prefix, and the
explicit live-run continuation rule below. The accepted economic, authority, safety, capacity,
command, and terminal-reconciliation requirements remain unchanged.

## Hermes integration checks

Hermes first proves `HEAD == origin/main` at this review's publication commit and reproves all
three accepted path hashes and line counts. It verifies that
`data/.cex002_open_interest_5m` does not exist and that at least 100 GiB is available. It then runs,
in order, stopping on the first nonzero result:

```bash
.venv/bin/python -m pytest tests/ingest/test_binance_usdm_open_interest.py -q --tb=short
.venv/bin/python -m ruff check src/cryptofactors/ingest/binance_usdm_open_interest.py scripts/research/normalize_binance_usdm_open_interest.py tests/ingest/test_binance_usdm_open_interest.py
python3 scripts/check_repo_control.py
```

No patch is authorized. A failed preflight or command is published honestly as record 422 and
stops before the real run.

## One real production run

After every check passes, Hermes launches exactly one durable detached invocation from the
repository root:

```bash
PYTHONPATH=src .venv/bin/python scripts/research/normalize_binance_usdm_open_interest.py \
  --generation0-state data/cex002_qualify/gate2/state.sqlite \
  --generation0-content-root data/cex002_qualify/gate2/content \
  --v3-manifest data/cex002_qualify/gate2_revision_candidate_v3/manifest/4dacaba97c17ad9c4a9724f5db74dfab7ee98760cdb3df6dea46ab37c0684c2d.json.gz \
  --recovery-root data/cex002_recovery \
  --output-root data/.cex002_open_interest_5m
```

The detached runner lives only beneath a literal `mktemp -d /tmp/cex002_oi_421_XXXXXX`
directory. It records the exact command, UTC start/end, shell and Python PID plus Linux start
ticks, stdout, stderr, and final exit code. It receives at least 48 hours wall allowance. A
one-shot Hermes harness ending is not authority to signal or kill the runner. No duplicate or
replacement invocation is allowed while the recorded process is live.

If a Hermes harness ends while the runner is live, it returns the exact runner directory, both
process identities and start ticks, start UTC, log paths, and current output counts without
publishing a terminal record. Later Hermes continuations under this same authorization may inspect
and poll only that recorded runner; they may not launch another. A power interruption permits only
the same command to resume the same hidden output root after reviewer disposition.

The accepted sizing evidence projects 280,534,938 rows, 19,744 symbol/month partitions, and
34,362,664,803 normalized bytes. These are capacity and duration expectations, not acceptance
counts; the real completion descriptor supplies the observed counts.

## Terminal evidence and integration publication

Hermes polls only the one recorded runner. On terminal success it reads the content-addressed
completion descriptor and reports its SHA-256, partition count, product row count, quality-gap row
count, output bytes by artifact class, authenticated authority counts, and the fixed HBAR conflict
row. It proves every descriptor-referenced file exists under the hidden root, has the named
digest, and reconciles its Parquet metadata row count. No second full replay is authorized.

At any terminal outcome Hermes publishes
`research/sprint_004/422_CEX002_OPEN_INTEREST_INTEGRATION_AND_REAL_RUN_RECORD.md`, updates
`docs/handoff/CURRENT_TASK.md` and `tickets/CEX-002.md` with both next-actor fields returned to the
reviewer, stages exactly those three records plus the three accepted developer paths, commits,
pushes, proves `HEAD == origin/main`, and stops. On failure it records the exact error and hidden
unreferenced partitions without patching, cleaning, retrying, or claiming a product.

No acquisition, network request, source/test patch, cleanup, deletion, other product, final
bundle, catalog transaction, NautilusTrader check, experiment, backtest, model, trading engine,
or next ticket is authorized.

## Reviewer publication scope

Under the AGENTS.md reviewer governance-publication exception, this review publishes exactly:

- `research/sprint_004/421_CEX002_LINT_CORRECTION_ACCEPTANCE_AND_REAL_RUN_REAUTHORIZATION.md`;
- `docs/handoff/CURRENT_TASK.md`; and
- `tickets/CEX-002.md`.

The accepted developer drop and every unrelated dirty path remain unstaged for Hermes.
