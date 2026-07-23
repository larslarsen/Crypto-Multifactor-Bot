# PAPER-003 — Paper Ops Monitoring and Hardening

**Priority:** P1
**Status:** READY
**Dependencies:** PAPER-002 (ACCEPTED), PROMO-002 (ACCEPTED)
**Layer:** execution / serving / ops
**Architecture:** Operational hardening of the factor-driven paper loop — persistence, health checks, and a minimal monitoring surface. No LIVE routing.

## Objective

Make paper trading operable day-to-day: persist session state and equity curves, expose a simple health/status report for `PAPER_APPROVED` artifacts, and fail closed on gate or data errors with structured ops logs.

## Scope

1. **Session persistence**
   - Persist paper account snapshots (cash, positions, equity, timestamp) and trade history to a control-plane or research path (SQLite table and/or JSONL under `research/sprint_004/paper_ops/`).
   - Support resume / append across runs for `mod_tsmom_30_7_v1` (or configurable `model_artifact_id`).

2. **Health / status report**
   - CLI or module that reports: promotion state, last rebalance time, last equity, open positions count, observation reference id, gate OK/fail.
   - Emit `research/sprint_004/09_PAPER_OPS_STATUS.json` (or equivalent).

3. **Hardening**
   - Structured error types for missing prices, empty factor frames, and promotion gate failures (no silent success).
   - Optional alert hook interface (callable / log-only stub) when equity drawdown exceeds a configurable threshold (default 10%).

4. **Tests**
   - Persistence round-trip; status report fields; drawdown alert fires once; gate failure still blocks loop.

## Out of Scope

- LIVE exchange connectivity or LIVE promotion.
- Full web UI/dashboard.
- New factor families.

## Acceptance (Jr)

1. `.venv/bin/python -m pytest tests/execution/ -q --tb=short`
2. `.venv/bin/python -m ruff check src/cryptofactors/execution scripts/`
3. `.venv/bin/python -m mypy --no-error-summary src/cryptofactors/execution`
4. Dry-run or script path producing status artifact
5. `python3 scripts/check_repo_control.py`

## Phased Ownership

- Sr Dev (Strong Model): production source. Stop for reviewer.
- Jr Dev (Weak Model): tests, gates, Git after approval.

## Stop Condition

After Sr: AWAITING_REVIEW, Next ticket authorized: NONE.
