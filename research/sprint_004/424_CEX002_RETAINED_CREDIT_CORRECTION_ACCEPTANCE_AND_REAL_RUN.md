# CEX-002 Review 424 — Retained-Credit Correction Acceptance and Real Run

- **Date:** 2026-09-01
- **Reviewer:** Lead Quantitative Finance Researcher/Engineer
- **Ticket:** CEX-002
- **Decision:** accept the surgical correction; authorize integration and one real production run
- **Gate 2:** `ACCEPTED`
- **Gate 3:** `IN_PROGRESS`
- **Next required actor:** Jr Dev — Hermes
- **Next ticket:** `NONE`

## Accepted corrective drop

Static inspection accepts the exact Review-423 two-path correction:

| Path | Lines | SHA-256 |
|---|---:|---|
| `src/cryptofactors/ingest/binance_usdm_open_interest.py` | 1,441 | `898c0a1a46d49961bef065d21251d8b79cf59b6f8676cd75df689fe6f3d336c1` |
| `tests/ingest/test_binance_usdm_open_interest.py` | 455 | `b36aa9e8da55affd03f63ebf01e500435a36dd27984bb646d6fd3e29c913e9b5` |

The CLI remains 53 lines at SHA-256
`33585315bb061a97d68197792ba86d8911383534d28c734f73f946900464a675`.

The correction imports the acquisition module's exact `OUTCOME_CHECKSUM_VERIFIED` and
`OUTCOME_RETAINED` constants, accepts only those two states through one helper called by the
generation-0 loader, and accurately rejects all others. Every existing schema, domain, singleton,
prefix, seal, count, provider/content-digest, byte-size, file-hash, and lineage check is unchanged.
The focused suite passed all 38 cases in Sol's sole authorized command.

## Hermes integration and source commit

Hermes first proves `HEAD == origin/main` at this review's publication commit and reproves the
three identities above. It verifies `data/.cex002_open_interest_5m` is absent and at least 100 GiB
is available. It then runs, in order, stopping on the first nonzero result:

```bash
.venv/bin/python -m pytest tests/ingest/test_binance_usdm_open_interest.py -q --tb=short
.venv/bin/python -m ruff check src/cryptofactors/ingest/binance_usdm_open_interest.py scripts/research/normalize_binance_usdm_open_interest.py tests/ingest/test_binance_usdm_open_interest.py
python3 scripts/check_repo_control.py
```

After all pass, Hermes stages exactly the accepted source and test paths, commits and pushes them,
and proves `HEAD == origin/main`. This integrates and pins the executable correction before the
long real run. No control record is changed in that integration commit. A failed preflight,
command, commit, or push is published honestly as record 425 and stops before the real run.

## One logged durable production run

Hermes then launches exactly one detached invocation from the repository root:

```bash
PYTHONPATH=src .venv/bin/python scripts/research/normalize_binance_usdm_open_interest.py \
  --generation0-state data/cex002_qualify/gate2/state.sqlite \
  --generation0-content-root data/cex002_qualify/gate2/content \
  --v3-manifest data/cex002_qualify/gate2_revision_candidate_v3/manifest/4dacaba97c17ad9c4a9724f5db74dfab7ee98760cdb3df6dea46ab37c0684c2d.json.gz \
  --recovery-root data/cex002_recovery \
  --output-root data/.cex002_open_interest_5m
```

The runner lives only under literal `mktemp -d /tmp/cex002_oi_424_XXXXXX`. A single detached
shell remains the parent of the single Python process, waits for it, and writes the final exit
code and end UTC. Before waiting, it records its own PID/start tick and the child Python PID/start
tick. The detached shell's stdout and stderr are redirected directly to persistent files in the
runner directory before launch; both files must exist immediately. The directory also records the
exact command, source commit, start UTC, and runner path. Hermes must verify the PID/start-tick
pairs and both log files after launch.

The processes receive at least 48 hours wall allowance and survive the one-shot harness. Hermes
must not run the command in the foreground, reproduce a failure, signal a live process, launch a
replacement, or delete any output or runner evidence. If the harness ends while the process is
live, it returns the exact runner metadata and current output counts without publishing a terminal
record. Later Hermes continuations under this review may inspect only that exact runner.

## Terminal evidence

On success Hermes performs Review 421's descriptor, partition, lineage, Parquet row, authority,
and HBAR-gap reconciliation without replaying the normalizer. At any terminal outcome it publishes
`research/sprint_004/425_CEX002_OPEN_INTEREST_REAL_RUN_RECORD.md`, updates CURRENT_TASK and the
ticket with both next-actor fields returned to the reviewer, stages exactly those three record
paths, commits, pushes, proves `HEAD == origin/main`, and stops. On failure it records the complete
captured stdout/stderr and existing hidden-output facts without patch, cleanup, reproduction, or
retry.

No acquisition, network request, source/test/CLI patch, deletion, other product, final bundle,
catalog transaction, NautilusTrader check, experiment, backtest, model, trading engine, or next
ticket is authorized.

Under the AGENTS.md reviewer governance-publication exception this review commits and pushes
exactly:

- `research/sprint_004/424_CEX002_RETAINED_CREDIT_CORRECTION_ACCEPTANCE_AND_REAL_RUN.md`;
- `docs/handoff/CURRENT_TASK.md`; and
- `tickets/CEX-002.md`.

The accepted source/test correction and every unrelated dirty path remain unstaged for Hermes.
