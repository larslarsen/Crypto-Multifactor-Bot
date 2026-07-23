# CURRENT_TASK

Ticket: PAPER-005
State: AWAITING_REVIEW
Next required actor: Lead Quantitative Finance Researcher/Engineer (reviewer)
Next ticket authorized: NONE

**Reviewer Decision (Architecture & Ticket Selection):**

DATA-003 ACCEPTED (REVIEW-0188). B5 fixed; factor compute works on adapter + real bars.

Authorizing **PAPER-005**: non-dry-run paper session on published real (or durable real-published) as-of bars; artifact `13_REAL_PAPER_SESSION.json`; `live_eligible: false` always in this ticket.

**Policy:** LIVE blocked until profitable real paper — this ticket only measures; does not promote LIVE.

## Implemented

- Backfilled all 10 mapped symbols via real Binance API into `control.db` + `data/store`.
- Published canonical `market_bars` dataset `ds_b92eb297f62313d9b0c7efc7dde5d6434891ae2dc37ea5e0cd7a8830bda2552f`.
- Ran `scripts/run_paper_momts.py` non-dry-run; real as-of factor session produced net return +1.37% across 8 decisions / 80 trades.
- Created `research/sprint_004/13_REAL_PAPER_SESSION.json` with `data_mode: real_asof`, `live_gate_satisfied: true`, `live_eligible: false`.
- Updated `research/sprint_004/08_PAPER_FACTOR_LOOP_RESULTS.json`, `09_PAPER_OPS_STATUS.json`, `10_PAPER_HARDEN_REPORT.json`, `11_REAL_DATA_PATH_REPORT.json`, `12_REAL_ASOF_CORRECTNESS.json`.
- Extended `scripts/research/backfill_binance_klines.py` with `--start-time` / `--end-time` CLI options.
- No LIVE. No live orders.

## Governing documents

- tickets/PAPER-005.md (AWAITING_REVIEW)
- tickets/DATA-003.md (ACCEPTED)
- docs/reviews/REVIEW-0188_DATA-003_ACCEPTED.md

## Acceptance (Jr)

1. .venv/bin/python -m pytest tests/acquisition/ tests/execution/ -q --tb=short
2. .venv/bin/python -m ruff check src/cryptofactors/execution scripts/
3. research/sprint_004/13_REAL_PAPER_SESSION.json present
4. python3 scripts/check_repo_control.py
