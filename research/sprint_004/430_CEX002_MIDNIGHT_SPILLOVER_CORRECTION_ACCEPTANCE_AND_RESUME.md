# CEX-002 Review 430 — Midnight-Spillover Correction Acceptance and Resume

- **Date:** 2026-09-01
- **Reviewer:** Lead Quantitative Finance Researcher/Engineer
- **Ticket:** CEX-002
- **Decision:** accept the bounded correction; authorize Hermes integration and one resume over the preserved hidden root
- **Gate 2:** `ACCEPTED`
- **Gate 3:** `IN_PROGRESS`
- **Next required actor:** Jr Dev — Hermes
- **Next ticket:** `NONE`

## Accepted corrective drop

Static inspection accepts Review 429's exact two-path correction:

| Path | Lines | SHA-256 |
|---|---:|---|
| `src/cryptofactors/ingest/binance_usdm_open_interest.py` | 1,493 | `bf6c5c445a6054c56d503f415388bc0df94e3326b621826fd0c378efa896387d` |
| `tests/ingest/test_binance_usdm_open_interest.py` | 576 | `3cd77872250130330898c83fa95196ba3e5b283633ba2809b2ac33b9d90fd9ad` |

The CLI remains 53 lines at SHA-256
`33585315bb061a97d68197792ba86d8911383534d28c734f73f946900464a675`.

Every physical row is still fully validated before contract-day classification. Exactly one row
at the immediately following UTC midnight may be excluded only when at least one owned-day row
remains. Any second exclusion or other out-of-day shape fails. The excluded row never enters the
product, duplicate, continuity, or stock/change stream. Its deterministic lineage binds the raw
source key and SHA-256, original physical ordinal, expected contract-day, observed UTC timestamp,
and fixed reason. The affected partition includes that fact and the completion descriptor counts
all excluded rows; unaffected partition lineage omits the new field and therefore remains
byte-identical.

The owned-boundary regression proves that the conflicting spillover is absent, the next-day-owned
value is retained, the original exclusion identity is recorded, the missing owned-day midnight is
a typed grid gap, and the completion count is exact. Non-midnight and nonadjacent out-of-day rows
remain rejected. Sol's sole targeted command passed all 42 cases:

```text
..........................................                               [100%]
```

## Preserved resume state and capacity

`data/.cex002_open_interest_5m` remains unchanged: eight content-addressed 0GUSDT Parquets and
eight matching lineage JSONs for 2025-09 through 2026-04, empty `.staging`, and no completion
descriptor. The accepted correction produces no new field in those unaffected lineages, so the
normalizer must verify and reuse their exact existing bytes. No deletion or cleanup is permitted.

The reviewer observed 105,263,493,120 available bytes at this review. The accepted
complete-product projection is 34,362,664,803 bytes. Applying ADR-0028's unchanged reserve rule gives a
21,052,698,624-byte operating reserve and a 55,415,363,427-byte requirement, leaving
49,848,129,693 bytes beyond that equation. This exact byte equation supersedes the earlier coarse
100-GiB launch check; it changes no sizing basis or reserve rule. Hermes must recompute the same
equation immediately before launch and stop before mutation if it is not sufficient.

## Hermes integration and resume sequence

Hermes first proves `HEAD == origin/main` at this review's publication commit, reproves all three
accepted identities above, and reproves the exact preserved hidden-root facts. It then runs in
order, stopping on the first nonzero result:

```bash
.venv/bin/python -m pytest tests/ingest/test_binance_usdm_open_interest.py -q --tb=short
.venv/bin/python -m ruff check src/cryptofactors/ingest/binance_usdm_open_interest.py scripts/research/normalize_binance_usdm_open_interest.py tests/ingest/test_binance_usdm_open_interest.py
python3 scripts/check_repo_control.py
```

After all pass, Hermes stages exactly the accepted source and test paths, commits and pushes them,
and proves `HEAD == origin/main`. No control record changes belong in that integration commit.

Hermes then launches exactly one logged detached invocation of the unchanged production command:

```bash
PYTHONPATH=src .venv/bin/python scripts/research/normalize_binance_usdm_open_interest.py \
  --generation0-state data/cex002_qualify/gate2/state.sqlite \
  --generation0-content-root data/cex002_qualify/gate2/content \
  --v3-manifest data/cex002_qualify/gate2_revision_candidate_v3/manifest/4dacaba97c17ad9c4a9724f5db74dfab7ee98760cdb3df6dea46ab37c0684c2d.json.gz \
  --recovery-root data/cex002_recovery \
  --output-root data/.cex002_open_interest_5m
```

The runner lives only beneath a literal `mktemp -d /tmp/cex002_oi_430_XXXXXX` directory. One
detached shell directly parents and waits for one Python process. The runner durably records the
exact source commit, command, UTC start/end, shell and Python PID plus Linux start ticks, stdout,
stderr, and final exit code. It receives at least 48 hours wall allowance and survives the
one-shot harness. It is a resume against the same hidden root, not a new download or acquisition run.

Hermes must not invoke the normalizer in the foreground, reproduce a failure, signal a live
process, launch a replacement, delete or clean the hidden root, or mutate an accepted existing
artifact. If the harness ends while the runner is live, it returns the exact runner directory,
both process identities/start ticks, start UTC, log paths, and current output counts without a
terminal record. Later Hermes continuations under this authorization may inspect only that exact
runner.

## Terminal evidence

On success Hermes performs the full descriptor, partition, lineage, Parquet-row, authority, gap,
and HBAR-conflict reconciliation required by Reviews 421, 424, and 427. It additionally proves
that all previously existing artifacts retained their exact bytes; the 0GUSDT May-2026 lineage
records the accepted May-03 spillover exclusion; the normalized May-04 00:00 value comes from the
May-04-owned source; the missing May-03 00:00 point is typed in the quality-gap product; and the
descriptor exclusion total reconciles every partition-lineage exclusion fact.

At any terminal outcome Hermes publishes
`research/sprint_004/431_CEX002_OPEN_INTEREST_RESUME_RECORD.md`, updates CURRENT_TASK and the ticket
with both next-actor fields returned to the reviewer, stages exactly those three record paths,
commits, pushes, proves `HEAD == origin/main`, and stops. On failure it records complete captured
logs and exact hidden-output facts without patch, cleanup, reproduction, or retry.

A failed preflight, check, or integration commit also publishes record 431 and stops before
launch. No acquisition, network request, source/test/CLI patch, other product, final bundle,
catalog transaction, NautilusTrader check, experiment, backtest, model, trading engine, or next
ticket is authorized.

Under the AGENTS.md reviewer governance-publication exception this review commits and pushes
exactly:

- `research/sprint_004/430_CEX002_MIDNIGHT_SPILLOVER_CORRECTION_ACCEPTANCE_AND_RESUME.md`;
- `docs/handoff/CURRENT_TASK.md`; and
- `tickets/CEX-002.md`.

The accepted source/test correction, preserved data, runner evidence, and unrelated dirty paths
remain unstaged and untouched for Hermes.
