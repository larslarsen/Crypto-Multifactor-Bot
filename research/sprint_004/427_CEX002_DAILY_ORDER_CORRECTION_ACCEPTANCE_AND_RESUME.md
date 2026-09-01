# CEX-002 Review 427 — Daily-Order Correction Acceptance and Resume

- **Date:** 2026-09-01
- **Reviewer:** Lead Quantitative Finance Researcher/Engineer
- **Ticket:** CEX-002
- **Decision:** accept the daily-order correction; authorize integration and one resume over the preserved hidden root
- **Gate 2:** `ACCEPTED`
- **Gate 3:** `IN_PROGRESS`
- **Next required actor:** Jr Dev — Hermes
- **Next ticket:** `NONE`

## Accepted corrective drop

Static inspection accepts Review 426's exact two-path correction:

| Path | Lines | SHA-256 |
|---|---:|---|
| `src/cryptofactors/ingest/binance_usdm_open_interest.py` | 1,448 | `b1ae591ed6f3cf9c77a649ac94fe9896c14431b4a837461c953a685128c073f4` |
| `tests/ingest/test_binance_usdm_open_interest.py` | 491 | `b597b69e14dfc656ed3194edfe82d474651083d3e4ed13146b169eab99419897` |

The CLI remains 53 lines at SHA-256
`33585315bb061a97d68197792ba86d8911383534d28c734f73f946900464a675`.

Each authenticated contract-day is fully parsed and validated into at most 288 five-minute grid
rows. The rows are stable-sorted by `create_time` before the existing duplicate, continuity,
stock-change, gap, and partition logic. Original `source_row_ordinal` and every raw value remain
unchanged. The new regression proves physical order `00:10, 00:00, 00:05` becomes economic order
with ordinals `[1, 2, 0]` and correct prior-stock/change values. Sol's sole targeted command passed
all 39 cases.

## Preserved partial root is resumable evidence

Review 425's hidden root `data/.cex002_open_interest_5m` is preserved. It contains exactly seven
content-addressed 0GUSDT Parquets and seven matching lineage JSONs for 2025-09 through 2026-03,
an empty `.staging`, and no completion descriptor. The normalizer's existing publication contract
verifies and reuses byte-identical content-addressed artifacts. The correction does not change the
rows in those already ordered months. Resume uses this exact root without deletion or cleanup;
the final descriptor is still published only after every required partition and gap artifact.

## Hermes integration and resume sequence

Hermes first proves `HEAD == origin/main` at this review's publication commit, reproves all three
accepted identities above, and reproves the exact preserved partial-root facts from record 425,
including hashes named by every existing content-addressed filename, empty staging, and absent
completion descriptor. It requires at least 100 GiB available. It then runs in order, stopping on
the first nonzero result:

```bash
.venv/bin/python -m pytest tests/ingest/test_binance_usdm_open_interest.py -q --tb=short
.venv/bin/python -m ruff check src/cryptofactors/ingest/binance_usdm_open_interest.py scripts/research/normalize_binance_usdm_open_interest.py tests/ingest/test_binance_usdm_open_interest.py
python3 scripts/check_repo_control.py
```

After all pass, Hermes stages exactly the accepted source and test paths, commits and pushes them,
and proves `HEAD == origin/main`. No control record changes in that integration commit.

Hermes then launches exactly one logged detached invocation of the same production command from
Review 424, using the same hidden output root, under literal
`mktemp -d /tmp/cex002_oi_427_XXXXXX`. It uses Review 424's proven runner contract: one detached
shell directly parents and waits for one Python process; exact source commit, command, UTC times,
PID/start-tick pairs, and runner path are recorded; stdout and stderr exist and are persistently
redirected before launch; exit code and end UTC are appended at terminal. The process receives at
least 48 hours wall allowance and survives the one-shot harness.

Hermes must not run the command in the foreground, reproduce a failure, signal a live process,
launch a replacement, delete or clean the hidden root, or mutate an accepted existing artifact.
If live at harness end, it returns exact identity/log/output status without a terminal record.
Later Hermes continuations may inspect only that exact runner.

## Terminal evidence

On success Hermes performs the full descriptor, partition, lineage, Parquet row, authority, gap,
and HBAR-conflict reconciliation required by Reviews 421 and 424, including proof that any reused
partial artifacts retained their exact bytes. At any terminal outcome it publishes
`research/sprint_004/428_CEX002_OPEN_INTEREST_RESUME_RECORD.md`, updates CURRENT_TASK and the ticket
with both next-actor fields returned to the reviewer, stages exactly those three record paths,
commits, pushes, proves `HEAD == origin/main`, and stops. On failure it records complete captured
logs and exact hidden-output facts without patch, cleanup, reproduction, or retry.

A failed preflight/check/integration commit also publishes record 428 and stops before launch. No
acquisition, network request, source/test/CLI patch, other product, final bundle, catalog
transaction, NautilusTrader check, experiment, backtest, model, trading engine, or next ticket is
authorized.

Under the AGENTS.md reviewer governance-publication exception this review commits and pushes
exactly:

- `research/sprint_004/427_CEX002_DAILY_ORDER_CORRECTION_ACCEPTANCE_AND_RESUME.md`;
- `docs/handoff/CURRENT_TASK.md`; and
- `tickets/CEX-002.md`.

The accepted source/test correction, preserved data, runner evidence, and unrelated dirty paths
remain unstaged and untouched for Hermes.
