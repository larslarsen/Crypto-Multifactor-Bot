# DATA-004 — Extend Real Market Bar History for Credible OOS

**Priority:** P0  
**Status:** ACCEPTED  
**Dependencies:** DATA-003, EXP-005 (ACCEPTED)  
**Layer:** acquisition / catalog / research evidence  
**Architecture:** reuse Binance fetcher + RAW→MAN→canonical bars path. **No LIVE. No risk-limit changes.**

## Objective

EXP-005 showed train-selected TSMOM winners fail a short holdout, but available `market_bars` only cover **2026-01-01 → 2026-07-23**. Credible walk-forward / multi-fold OOS needs **much longer** real history (target: **≥24 months** ending at latest available, or document venue max if shorter).

## Scope

1. **Backfill** the paper universe (same 10 names / Binance spot maps) to the extended range via existing acquisition pipeline.
2. **Publish** content-addressed RAW + MAN + canonical `market_bars`; record new `dataset_id` and date span in artifact.
3. **Artifact** `research/sprint_004/20_EXTENDED_HISTORY_REPORT.json`:
   - `bar_start`, `bar_end`, per-symbol row counts / gaps
   - `canonical_dataset_id`, store roots (no secrets)
   - `live_eligible: false`
4. **Do not** re-run full TSMOM LIVE claims in this ticket (optional smoke: one factor session may be noted but not required).
5. **Do not mutate** artifacts 08–19 (append-only).
6. **Tests:** existing suite green; fetcher/path tests if touched.

## Out of Scope

- LIVE / paper promotion  
- Changing TSMOM params or risk limits  
- New venues beyond current Binance spot path  

## Acceptance (Jr)

1. `.venv/bin/python -m pytest tests/execution/ tests/acquisition/ -q --tb=short`
2. `.venv/bin/python -m ruff check src/cryptofactors/execution src/cryptofactors/acquisition scripts/`
3. `20_EXTENDED_HISTORY_REPORT.json` present; span ≥24 months **or** explicit `venue_max_reached: true` with documented end/start
4. `python3 scripts/check_repo_control.py`

## Stop Condition

After Sr: AWAITING_REVIEW, Next ticket authorized: NONE.
