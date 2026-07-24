# INFRA-001 — Automated Daily Bar Refresh + Paper Loop Scheduler

**Priority:** P0  
**Status:** ACCEPTED  
**Dependencies:** ARCH-001 (ACCEPTED), DATA-005 (ACCEPTED)  
**Layer:** ops / acquisition / execution orchestration  
**Architecture:** Local-first batch jobs only. No cloud daemons. No LIVE. No new factors.

## Objective

While the contaminated research window (through 2026-07-23) is closed and the holdout starts 2026-07-24, build a **deterministic, idempotent daily ops path** that:

1. Refreshes Binance spot daily klines into the catalog (BAR-001 → PASS path).
2. Optionally runs a **paper** loop on a pinned config (or a dry-run stub if no pre-registered factor is active).
3. Emits a single machine-readable ops report for the day.

This accumulates fresh holdout bars without manual intervention and keeps ops reviewable.

## Scope

1. **Daily refresh runner** (`scripts/ops/daily_refresh.py` or equivalent under `scripts/`):
   - Pull incremental BIN-001 source for the configured universe (same 10 symbols as research path unless config says otherwise).
   - Publish/rebuild canonical `market_bars` via BAR-001 (transform v6+; native 1d eligible).
   - Prefer/register PASS quality; pin dataset id in the report.
   - Idempotent: safe to re-run same calendar day.
2. **Paper loop step** (optional flag, default off or dry-run):
   - If no active pre-registered factor: emit `paper_skipped: true` with reason (no LIVE, no archived TSMOM reuse).
   - Do **not** run `tsmom_14_3` / `mod_tsmom_14_3_v1` (archived false discovery).
3. **Ops artifact** `research/sprint_004/30_DAILY_OPS_REPORT.json` (or dated under `research/ops/` if preferred — pick one and stick to it):
   - run_at, bars span start/end, new_bar_count, canonical_dataset_id, quality_status
   - holdout_start: 2026-07-24; bars_in_holdout_count
   - paper_skipped / paper metrics if run
   - live_eligible: false
4. **Scheduler entry** — document one local mechanism only:
   - e.g. example crontab line **or** a small `scripts/ops/run_daily.sh` wrapper
   - No systemd/cloud requirement; document in ticket change report or short ops note under `docs/ops/` if needed.
5. **Tests** for idempotency / dry-run path; suite green on touched areas.
6. **Do not** authorize LIVE, re-tune factors, or un-archive tsmom_14_3.

## Out of Scope

- LIVE_APPROVED / broker order routing  
- New factor research or grid search  
- Cloud schedulers, always-on daemons without ADR  
- Using contaminated pre-holdout window for selection  

## Acceptance (Jr)

1. `.venv/bin/python -m pytest tests/ -q --tb=short` (or scoped acquisition/market/execution if full suite too slow)
2. `.venv/bin/python -m ruff check src/cryptofactors scripts/`
3. Ops report present after a successful dry-run or one real refresh
4. `python3 scripts/check_repo_control.py`

## Stop Condition

After Sr: AWAITING_REVIEW, Next ticket authorized: NONE.
