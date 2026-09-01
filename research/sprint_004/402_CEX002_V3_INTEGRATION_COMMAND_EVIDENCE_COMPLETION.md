# CEX-002 V3 Integration Command-Evidence Completion Record 402

- **Date:** 2026-09-01
- **Evidence actor:** Jr Dev - Hermes
- **Reviewer:** Lead Quantitative Finance Researcher/Engineer
- **Ticket:** CEX-002
- **Decision:** publish evidence-only correction of record-400 command/count defects; no rerun
- **Gate 2:** `IN_PROGRESS`
- **Next ticket:** `NONE`

## Accepted integration facts (from Review 401, no rerun)

The reviewer-accepted integration commit and its authority are taken verbatim from
Review 401 and record 400. No Python, pytest, ruff, collect-only, planner, network,
SQLite, real candidate/data, acquisition, cleanup, transition, later gate, or later-ticket
action was performed while writing this record.

- **Integration commit:** `fd61a7db42acd48d32a85f55e6406c90e83c2603`
- **Parent commit:** `5421cfb11ba0af97ed51c9c5ce86d1b20c1d1f67` (Review 399 publication commit)
- **Exactly five committed paths:**
  1. `src/cryptofactors/acquisition/binance_usdm_gate2_revision_candidate.py`
  2. `tests/acquisition/test_binance_usdm_gate2_revision_candidate.py`
  3. `research/sprint_004/400_CEX002_V3_REACHABILITY_INTEGRATION_RECORD.md`
  4. `docs/handoff/CURRENT_TASK.md`
  5. `tickets/CEX-002.md`
- **Production source identity:** SHA-256 `1ac17e902ea3b8aa6967ad3cb4e89d2b2b746f147eb1f83322fba2776e107e32` at 5,147 lines
- **Test source identity:** SHA-256 `a715023e8e8c43ef908097c4bb7332cfcc4798d08929d433223f4e149599b905` at 3,342 lines and 70 test functions
- **Targeted pytest result:** exit 0, 147 cases passed in 39.87 seconds, no reported warnings
- **Targeted ruff result:** exit 0, `All checks passed!`
- **Repository control result:** exit 0, `Repo control check: PASS`
- **Scoped diff check result:** exit 0, empty stdout/stderr
- **Remote equality:** `HEAD == origin/main == fd61a7db42acd48d32a85f55e6406c90e83c2603` at integration time; current HEAD is the Review-401 publication commit `d3a947d449479a52107ac7f85e89d791e5d4f5a5` and `HEAD == origin/main`
- **Staging:** empty
- **No candidate, manifest, receipt, lineage, locator, v3 candidate, Gate-2 result, transition, or later ticket is accepted.**

## Corrected preflight path classification

Record 400 states that 13 unrelated modified paths were preserved but enumerates only the
actual 11 unrelated modified paths. Before the `fd61a7d` integration there were 13 modified
paths total: **two were the accepted developer drop** (`src/cryptofactors/acquisition/binance_usdm_gate2_revision_candidate.py`
and `tests/acquisition/test_binance_usdm_gate2_revision_candidate.py`) and **exactly 11 were unrelated**.
After the five-path commit, the same **11 unrelated modified** and **13 unrelated untracked**
paths remain. Record 400 and the harness summary conflated total modified paths with unrelated
modified paths.

The 11 unrelated modified paths preserved unstaged are:
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

The 13 unrelated untracked paths preserved are:
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

## Exact collect-only truth

**A separate `--collect-only` command did NOT run.**

Record 400's pytest section states:
```text
Collected cases: 147 (confirmed via `--collect-only`: `tests/acquisition/test_binance_usdm_gate2_revision_candidate.py: 147`).
```

Review 399 authorized exactly four commands. Record 400 enumerates exactly four commands:
1. `PYTHONPATH=src .venv/bin/python -m pytest -q tests/acquisition/test_binance_usdm_gate2_revision_candidate.py`
2. `.venv/bin/python -m ruff check --no-cache src/cryptofactors/acquisition/binance_usdm_gate2_revision_candidate.py tests/acquisition/test_binance_usdm_gate2_revision_candidate.py`
3. `python3 scripts/check_repo_control.py`
4. `git diff --check -- src/cryptofactors/acquisition/binance_usdm_gate2_revision_candidate.py tests/acquisition/test_binance_usdm_gate2_revision_candidate.py docs/handoff/CURRENT_TASK.md research/sprint_004/400_CEX002_V3_REACHABILITY_INTEGRATION_RECORD.md tickets/CEX-002.md`

Command 1 is a **standard pytest run** (no `--collect-only` flag), and its recorded output is
the standard test-execution summary `147 passed in 39.87s`. A `--collect-only` invocation
would require the `--collect-only` flag and would emit a collected-items list, not a
`147 passed` execution summary. No `--collect-only` command appears in the command list, no
collect-only output appears in any recorded stream, and Review 399 authorized exactly four
commands without any collect-only variant.

**Origin of the false attribution:** the standard pytest run's own `147 passed` summary
reports the case count directly. Record 400's author misattributed that count to a separate
`--collect-only` invocation that never occurred. The `147` figure is correct; the claimed
collect-only mechanism is not.

**Explicit classification:** any separate `--collect-only` command would have been
unauthorized, because Review 399 authorized exactly the four listed commands and no
additional Python/test invocation.

## No further command authorization

No further Python, pytest, ruff, collect-only, planner, network, SQLite, real
candidate/data, acquisition, cleanup, transition, later gate, or later-ticket action may be
run to reconstruct missing output. The integration evidence chain is now corrected by this
record without any rerun.

## Stop

CEX-002 and Gate 2 remain `IN_PROGRESS`. Next ticket remains `NONE`. Record 400,
integrated source/test, real data, and every unrelated dirty path remain unchanged and
unstaged.
