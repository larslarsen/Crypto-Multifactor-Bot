# CEX-002 Review 417 — Open-Interest Source Acceptance, Integration, and Real Run

- **Date:** 2026-09-01
- **Reviewer:** Lead Quantitative Finance Researcher/Engineer
- **Ticket:** CEX-002
- **Decision:** accept the corrected source for integration and one real production run
- **Gate 2:** `ACCEPTED`
- **Gate 3:** `IN_PROGRESS`
- **Next required actor:** Jr Dev — Hermes
- **Next ticket:** `NONE`

## Accepted unintegrated source drop

Static review accepts the Review-416 correction at these exact identities:

| Path | Lines | SHA-256 |
|---|---:|---|
| `src/cryptofactors/ingest/binance_usdm_open_interest.py` | 1,432 | `c2b8835445036359e870cb6a3fa77907bc9ec766a2e1da355ef837e7c22a70d8` |
| `scripts/research/normalize_binance_usdm_open_interest.py` | 53 | `33585315bb061a97d68197792ba86d8911383534d28c734f73f946900464a675` |
| `tests/ingest/test_binance_usdm_open_interest.py` | 440 | `aee598c17cbd7fc2c4835a924c03fc4f0e9cc3570b68da20c02706b39afd92b0` |

Sol's one Review-416 targeted command exited 0 with all 35 cases passing:

```text
...................................                                      [100%]
```

The correction pins the exact v3 manifest; authenticates generation 0's schema, domains,
singletons, complete sealed prefix, run-7 head, clean tail, and exact metrics count through a
borrowed read-only connection; publishes exact typed missing-run gaps; publishes one final hidden
completion descriptor last; holds every output child no-follow; and rejects impossible negative
economics. The source implements only `binance_usdm_open_interest_5m`. It is accepted for Hermes
integration and real execution, not yet as a real data product.

## Hermes integration and command sequence

Hermes must first prove `HEAD == origin/main` at this review's publication commit and reprove all
three accepted path hashes and line counts. It then runs, in order, stopping on the first nonzero
result:

```bash
.venv/bin/python -m pytest tests/ingest/test_binance_usdm_open_interest.py -q --tb=short
.venv/bin/python -m ruff check src/cryptofactors/ingest/binance_usdm_open_interest.py scripts/research/normalize_binance_usdm_open_interest.py tests/ingest/test_binance_usdm_open_interest.py
python3 scripts/check_repo_control.py
```

No patch is authorized. A failure is published honestly and stops before the real run.

## One real production run

After all three integration checks pass, Hermes launches exactly one durable detached invocation
of this command from the repository root:

```bash
PYTHONPATH=src .venv/bin/python scripts/research/normalize_binance_usdm_open_interest.py \
  --generation0-state data/cex002_qualify/gate2/state.sqlite \
  --generation0-content-root data/cex002_qualify/gate2/content \
  --v3-manifest data/cex002_qualify/gate2_revision_candidate_v3/manifest/4dacaba97c17ad9c4a9724f5db74dfab7ee98760cdb3df6dea46ab37c0684c2d.json.gz \
  --recovery-root data/cex002_recovery \
  --output-root data/.cex002_open_interest_5m
```

The detached runner lives only beneath a literal `mktemp -d /tmp/cex002_oi_417_XXXXXX` directory.
It records the exact command, UTC start/end, shell and Python PID plus Linux start ticks, stdout,
stderr, and final exit code. It receives at least 48 hours wall allowance. A one-shot Hermes
harness ending is not authority to kill the runner. No duplicate or replacement invocation is
allowed while the recorded process is live. A power interruption permits only the same command to
resume the same hidden output root after reviewer disposition; it does not reopen acquisition.

The accepted sizing evidence projects 280,534,938 rows, 19,744 symbol/month partitions, and
34,362,664,803 normalized bytes for this product. These are capacity and duration expectations,
not acceptance counts: the real descriptor supplies the observed counts. The run must retain at
least the currently available 100 GiB before launch; otherwise it stops before mutation.

## Terminal evidence and integration publication

Hermes polls only the one recorded runner. On terminal success it reads the content-addressed
completion descriptor and reports its SHA-256, partition count, product row count, quality-gap row
count, output bytes by artifact class, authenticated authority counts, and the fixed HBAR conflict
row. It proves every descriptor-referenced file exists under the hidden root, has the named digest,
and reconciles its Parquet metadata row count. No second full replay is authorized in this run.

Hermes publishes `research/sprint_004/418_CEX002_OPEN_INTEREST_INTEGRATION_AND_REAL_RUN_RECORD.md`,
updates `docs/handoff/CURRENT_TASK.md` and `tickets/CEX-002.md` with both next-actor fields returned
to the reviewer, stages exactly those three records plus the three accepted developer paths,
commits, pushes, proves `HEAD == origin/main`, and stops. If the runner fails, the same record must
state the exact terminal error and any hidden unreferenced partitions; it must not patch, clean,
retry, or claim a product.

No acquisition, network request, source/test patch, cleanup, deletion, other product, final bundle,
catalog transaction, NautilusTrader check, experiment, backtest, model, trading engine, or next
ticket is authorized.

## Reviewer publication scope

Under the AGENTS.md reviewer governance-publication exception, this review publishes exactly:

- `research/sprint_004/417_CEX002_OPEN_INTEREST_SOURCE_ACCEPTANCE_INTEGRATION_AND_REAL_RUN.md`;
- `docs/handoff/CURRENT_TASK.md`; and
- `tickets/CEX-002.md`.

The accepted developer drop and every unrelated dirty path remain unstaged for Hermes.
