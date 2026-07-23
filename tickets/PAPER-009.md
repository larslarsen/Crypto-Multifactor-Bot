# PAPER-009 — Re-Validate Frozen tsmom_14_3 on PASS Bars + Pin Dataset

**Priority:** P0  
**Status:** ACCEPTED  
**Dependencies:** DATA-005 (ACCEPTED), PAPER-008  
**Layer:** paper evidence / catalog discovery  
**Architecture:** frozen config only; PASS dataset pin. **No LIVE. No lookback/skip change.**

## Objective

DATA-005 produced PASS bars (`ds_0cb6415fa79119bf5317c124e9da2f0d4953b9a8d119aae45e2589ba716c5aaa`) but `resolve_latest_by_type` still returns REJECTED history (epoch `created_at`). Re-run **frozen** `tsmom_14_3` paper on the **PASS** dataset (explicit pin). Optionally fix resolve_latest to prefer PASS / real timestamps.

## Scope

1. **Pin** PASS dataset id above (do not rely on resolve_latest unless fixed and tested).
2. **Re-run** frozen `tsmom_14_3` / `mod_tsmom_14_3_v1` (or same economic identity) full window 2024-04-01 → 2026-07-23, ALLOC-001 risk, weekly — same protocol as PAPER-008.
3. **Artifact** `research/sprint_004/26_TSMOM_14_3_PASS_BARS_PAPER.json`:
   - session metrics; `dataset_id`; `quality_status: PASS`
   - `candidate_frozen: true`; `live_eligible: false`
   - compare to PAPER-008 return (document delta)
4. **Catalog fix (required if touching catalog):** `resolve_latest_by_type` must not prefer REJECTED over newer PASS when timestamps are equal — e.g. order by quality (PASS first) then `created_at`/`dataset_id`, **and/or** set real `created_at` on publish. Add test.
5. **Do not** change lookback/skip; do not mutate 08–25.
6. **Tests:** suite green including any new catalog/bar tests.

## Out of Scope

- LIVE promotion  
- Parameter search  
- Risk limit changes  

## Acceptance (Jr)

1. `.venv/bin/python -m pytest tests/execution/ tests/acquisition/ tests/market/ -q --tb=short`
2. `.venv/bin/python -m ruff check src/cryptofactors scripts/`
3. `26_TSMOM_14_3_PASS_BARS_PAPER.json` present; quality PASS; `live_eligible: false`
4. `python3 scripts/check_repo_control.py`

## Stop Condition

After Sr: AWAITING_REVIEW, Next ticket authorized: NONE.
