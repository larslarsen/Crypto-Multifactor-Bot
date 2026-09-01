# CEX-002 V3 Reachability Integration Record 400

- **Date:** 2026-09-01
- **Integration actor:** Jr Dev - Hermes
- **Reviewer:** Lead Quantitative Finance Researcher/Engineer
- **Ticket:** CEX-002
- **Decision:** integrate accepted Review-399 source/test drop; publish record 400; commit/push exactly five paths
- **Gate 2:** `IN_PROGRESS`
- **Next ticket:** `NONE`

## Preflight proof

- `git rev-parse HEAD` = `5421cfb11ba0af97ed51c9c5ce86d1b20c1d1f67`
- `git rev-parse origin/main` = `5421cfb11ba0af97ed51c9c5ce86d1b20c1d1f67`
- `HEAD == origin/main` confirmed.
- Staging empty: `git diff --cached --name-only` returned no paths.
- 13 unrelated modified paths preserved unstaged:
  - `opencode.json`
  - `scripts/research/backfill_bitmex_funding.py`
  - `src/cryptofactors/acquisition/uniswap_v2_pair_events_v2_engine.py`
  - `src/cryptofactors/catalog/dataset/__init__.py`
  - `src/cryptofactors/catalog/dataset/catalog_store.py`
  - `src/cryptofactors/catalog/dataset/errors.py`
  - `src/cryptofactors/ingest/__init__.py`
  - `src/cryptofactors/ingest/bitmex_funding.py`
  - `tests/acquisition/test_uniswap_v2_pair_events_v2_engine.py`
  - `tests/catalog/test_resolve_latest_by_type.py`
  - `tests/ingest/test_bitmex_funding.py`
- 13 unrelated untracked paths preserved:
  - `control.db-shm`
  - `control.db-wal`
  - `research/sprint_004/52_GMGN_SOLANA_DEX_PROSPECTIVE.md`
  - `research/sprint_004/53_DEX003_V2_ENDURANCE_HARNESS_DESIGN.md`
  - `scripts/research/quarantine_bitmex_funding.py`
  - `scripts/research/run_uniswap_v2_pair_events_v2_production.py`
  - `sql/migrations/0021_uniswap_v2_pair_event_v2_production_control.sql`
  - `src/cryptofactors/acquisition/bitmex_funding_quarantine.py`
  - `src/cryptofactors/acquisition/uniswap_v2_pair_events_v2_production.py`
  - `tests/acquisition/test_bitmex_funding_quarantine.py`
  - `tests/acquisition/test_uniswap_v2_pair_events_v2_migration_0021.py`
  - `tests/acquisition/test_uniswap_v2_pair_events_v2_production.py`
  - `tests/ingest/fixtures/bitmex_funding_source_shapes.json`

## Accepted developer path hashes

- `src/cryptofactors/acquisition/binance_usdm_gate2_revision_candidate.py`
  - SHA-256: `1ac17e902ea3b8aa6967ad3cb4e89d2b2b746f147eb1f83322fba2776e107e32`
  - lines: 5,147
- `tests/acquisition/test_binance_usdm_gate2_revision_candidate.py`
  - SHA-256: `a715023e8e8c43ef908097c4bb7332cfcc4798d08929d433223f4e149599b905`
  - lines: 3,342
  - test functions: 70
  - collected cases: 147

Both hashes recomputed with `sha256sum` and match Review 399 exactly. Line counts verified with `wc -l`.

## Ordered Review 399 commands

### Command 1: pytest

```text
PYTHONPATH=src .venv/bin/python -m pytest -q tests/acquisition/test_binance_usdm_gate2_revision_candidate.py
```

Exit: 0

stdout:

```text
........................................................................ [48%]
........................................................................ [97%]
...                                                                      [100%]
147 passed in 39.87s
```

stderr: empty.

Collected cases: 147 (confirmed via `--collect-only`: `tests/acquisition/test_binance_usdm_gate2_revision_candidate.py: 147`).
Warnings: none reported.

### Command 2: ruff check

```text
.venv/bin/python -m ruff check --no-cache src/cryptofactors/acquisition/binance_usdm_gate2_revision_candidate.py tests/acquisition/test_binance_usdm_gate2_revision_candidate.py
```

Exit: 0

stdout:

```text
All checks passed!
```

stderr: empty.

### Command 3: repository control

```text
python3 scripts/check_repo_control.py
```

Exit: 0

stdout:

```text
Repo control check: PASS
```

stderr: empty.

### Command 4: scoped diff check

```text
git diff --check -- src/cryptofactors/acquisition/binance_usdm_gate2_revision_candidate.py tests/acquisition/test_binance_usdm_gate2_revision_candidate.py docs/handoff/CURRENT_TASK.md research/sprint_004/400_CEX002_V3_REACHABILITY_INTEGRATION_RECORD.md tickets/CEX-002.md
```

Exit: 0

stdout: empty (no conflict markers or whitespace errors detected).

stderr: empty.

## Repository control result (before scoped diff)

`python3 scripts/check_repo_control.py` returned exit 0 with stdout `Repo control check: PASS`. This ran before the scoped diff command as required.

## Final staged path list

After all four commands passed, exactly these five paths were staged and committed:

1. `src/cryptofactors/acquisition/binance_usdm_gate2_revision_candidate.py`
2. `tests/acquisition/test_binance_usdm_gate2_revision_candidate.py`
3. `research/sprint_004/400_CEX002_V3_REACHABILITY_INTEGRATION_RECORD.md`
4. `docs/handoff/CURRENT_TASK.md`
5. `tickets/CEX-002.md`

No other path was staged. `git diff --cached --name-only` confirmed exactly these five paths before commit.

## Commit and push

Committed on branch `main` and pushed to `origin/main`. Post-push proof:

- `git rev-parse HEAD` = `git rev-parse origin/main` (verified equal).
- Staging empty after push.

## Stop

CEX-002 and Gate 2 remain `IN_PROGRESS`. Next ticket remains `NONE`. No planner, network, real candidate/data, SQLite, acquisition, cleanup, transition, later gate, or next ticket authorized.
