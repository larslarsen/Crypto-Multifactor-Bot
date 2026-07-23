# PAPER-005 — Real As-Of Paper Session Evidence

**Priority:** P0  
**Status:** AWAITING_REVIEW  
**Dependencies:** DATA-003 (ACCEPTED), PAPER-004, HARDEN-001  
**Layer:** execution / research evidence  
**Architecture:** use existing backfill + paper loop. **No LIVE. No LIVE_APPROVED.**

## Objective

Produce a **non-synthetic** paper session artifact against published canonical `market_bars` (real API backfill preferred; if network blocked in env, document and use longest available real-published dataset already on disk). Record whether net return is positive — this feeds the LIVE gate policy.

## Scope

1. **Backfill** at least BTC+ETH (or full mapped universe if feasible) via non-`--dry-run` Binance path into durable `control.db` + store root (paths documented, not secrets).
2. **Run** `scripts/run_paper_momts.py` **without** `--dry-run` against that DB/store/dataset id.
3. **Artifacts** under `research/sprint_004/`:
   - Update or write paper loop results + ops status + `12_REAL_ASOF_CORRECTNESS.json` with `data_mode: real_asof`, `live_eligible: false`
   - New `13_REAL_PAPER_SESSION.json` summarizing: dataset ids, date range, net return, trade count, observation ref, `live_gate_satisfied: false` unless net return > 0 **and** real_asof (still do not set live_eligible true without explicit LIVE ticket)
4. **Tests:** keep existing; add only if new helpers appear. No live order tests.
5. **Fail closed** if no real bars / empty prices.

## Out of Scope

- LIVE promotion, API keys in git, funded orders  
- Changing factor definition  
- Claiming LIVE eligibility (even if profitable — requires separate LIVE ticket + owner policy)

## Acceptance (Jr)

1. `.venv/bin/python -m pytest tests/acquisition/ tests/execution/ -q --tb=short`
2. `.venv/bin/python -m ruff check src/cryptofactors/execution scripts/`
3. Artifact `13_REAL_PAPER_SESSION.json` exists with `data_mode` and `live_eligible: false`
4. `python3 scripts/check_repo_control.py`

## Stop Condition

After Sr: AWAITING_REVIEW, Next ticket authorized: NONE.
