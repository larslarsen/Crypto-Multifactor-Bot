# CEX-002 Review 471 - Corrected Funding Test Acceptance and Real Run

- **Date:** 2026-09-02
- **Reviewer:** Lead Quantitative Finance Researcher/Engineer
- **Ticket:** CEX-002
- **Decision:** accept the exact test-fixture correction for Hermes integration and one real run
- **Gate 2:** `ACCEPTED`
- **Gate 3:** `IN_PROGRESS` - four of eleven required products accepted
- **Next required actor:** Jr Dev - Hermes
- **Next ticket:** `NONE`

## Accepted unintegrated source

Static review accepts the complete three-path realized-funding drop at these exact identities:

| Path | Lines | SHA-256 |
|---|---:|---|
| `src/cryptofactors/ingest/binance_usdm_funding_realized.py` | 1,404 | `4e38658f89905e1f5b66b739eb8f58e2f66ce204b9c61cfbfa7cb0ed161acada` |
| `scripts/research/normalize_binance_usdm_funding_realized.py` | 50 | `05e30c8712608e4895749114375a9b38ea5cf868870d913ddef5d264f77d7b2b` |
| `tests/ingest/test_binance_usdm_funding_realized.py` | 907 | `b7b9add7396ff8a3bac4717ae60a7048f7282b0a0117b27c14bfe55d978a0183` |

Grok changed only the authorized test behavior: it unlinks the exact sidecar left by the preceding
two cases and proves that path absent before the unchanged missing-sidecar assertion. Production
and CLI remain byte-identical to their Review-468 accepted identities. No Grok test output was
relayed to the reviewer, so no senior test result is accepted; Hermes must run the full focused
suite before integration. No data defect was found, and no download is required.

## Hermes integration

Hermes must prove `HEAD == origin/main` at this review's publication commit and reprove all three
accepted hashes and line counts. Hermes then runs these commands in order, stopping on the first
nonzero result:

```bash
PYTHONPATH=src .venv/bin/python -m pytest tests/ingest/test_binance_usdm_funding_realized.py -q --tb=short
PYTHONPATH=src .venv/bin/python -m ruff check src/cryptofactors/ingest/binance_usdm_funding_realized.py scripts/research/normalize_binance_usdm_funding_realized.py tests/ingest/test_binance_usdm_funding_realized.py
python3 scripts/check_repo_control.py
```

No patch is authorized. If all commands pass, Hermes stages exactly the three accepted developer
paths, commits them with message `CEX-002: integrate realized funding normalizer`, pushes, and
proves `HEAD == origin/main`. No unrelated path is staged.

## One real realized-funding run

After integration, Hermes proves that `data/.cex002_funding_realized` is absent and not a symlink,
no matching funding normalizer is running, and `df -B1 --output=avail data` is at least
110,648,021,942 bytes. The execution mechanism must permit at least 3,600 seconds before launch.
Hermes then executes exactly once in the foreground and remains attached until terminal:

```bash
PYTHONPATH=src .venv/bin/python scripts/research/normalize_binance_usdm_funding_realized.py \
  --generation0-state data/cex002_qualify/gate2/state.sqlite \
  --generation0-content-root data/cex002_qualify/gate2/content \
  --report research/sprint_004/62_CEX002_GATE1_SOURCE_PROCUREMENT.json \
  --sizing research/sprint_004/258_CEX002_GATE2_STORAGE_SIZING_V3.json \
  --output-root data/.cex002_funding_realized
```

This reads the already downloaded and authenticated funding files locally. It performs no network
access and does not alter generation 0. There is no wrapper, detach, retry, replay, second
invocation, cleanup, or polling loop. A nonzero result is recorded exactly and stops without
patching or deleting partial artifacts.

On success Hermes records exact stdout, exit code, wall time, pre/post available bytes, completion
path and SHA-256, schema and normalizer SHA-256, source count/bytes/state split, physical/collapsed/
product row equation, event-time and interval ranges, interval histogram, partition/lineage counts
and bytes, sole-completion state, and staging inventory. Hermes independently verifies every
descriptor-referenced partition and lineage file, its containment, regular-file status, digest,
Parquet schema, and row count, then reconciles all sums to the completion equation.

Hermes publishes `research/sprint_004/472_CEX002_FUNDING_INTEGRATION_AND_REAL_RUN_RECORD.md`, updates
`docs/handoff/CURRENT_TASK.md` and `tickets/CEX-002.md`, returns both actor fields to the reviewer,
stages exactly those three record paths, commits, pushes, proves `HEAD == origin/main`, and stops.

No acquisition, source/test correction, deletion, cleanup, other product, coverage product, bundle,
catalog transaction, NautilusTrader check, experiment, model, Harmonic Trader work, PAPER, LIVE, or
next-ticket work is authorized.

## Reviewer publication scope

Under the AGENTS.md reviewer governance-publication exception, this review publishes exactly:

- `research/sprint_004/471_CEX002_CORRECTED_FUNDING_TEST_ACCEPTANCE_AND_REAL_RUN.md`;
- `docs/handoff/CURRENT_TASK.md`; and
- `tickets/CEX-002.md`.

All developer source/test/CLI, data, runner, acceptance-command, and unrelated dirty paths remain
unstaged and untouched until Hermes performs the exact workflow above.
