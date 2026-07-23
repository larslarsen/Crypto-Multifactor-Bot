# PAPER-007 — Risk-Compliant Paper Evidence for tsmom_14_0 on Extended History

**Priority:** P0  
**Status:** AWAITING_REVIEW  
**Dependencies:** EXP-006 (ACCEPTED), DATA-004, ALLOC-001  
**Layer:** execution / paper / research evidence  
**Architecture:** ALLOC-001 risk; real as-of on DATA-004 dataset. **No LIVE.**

## Objective

EXP-006 multi-fold OOS favors **`tsmom_14_0`** among frozen configs (gates 2/3; best approximate compound). Produce a single **risk-compliant real as-of paper session** on the extended history as promotion-grade *evidence* (still not LIVE).

## Scope

1. **Primary config:** `tsmom_14_0` (lookback=14, skip=0). Optional secondary note for `tsmom_14_3` only if cheap; not required.
2. **Data:** Pin DATA-004 canonical  
   `ds_a17651d5c871656f18c29d50fe96d41fa9f08eee8436b276237f96a679764dcd`  
   Document quality REJECTED / 1d caveat.
3. **Window:** Full usable decision span after 90d warmup (e.g. 2024-04-01 → 2026-07-23 weekly) **or** document a pre-registered paper window; must be real_asof.
4. **Risk:** ALLOC-001 neutrality-preserving 0.15 / 1.0; report max |w|, gross, max |net|.
5. **Model identity:** Prefer a **new** research `model_artifact_id` for `tsmom_14_0` (do not pretend it is `mod_tsmom_30_7_v1` economically). If paper loop requires PAPER_APPROVED plumbing, document the registration path; do not claim LIVE eligibility.
6. **Artifact** `research/sprint_004/22_TSMOM_14_0_PAPER_SESSION.json`:
   - net return, trades, risk metrics, `meets_risk_limits`, `is_complete`, `live_gate_satisfied`, **`live_eligible: false`**
   - fold-cross-ref to EXP-006
7. **Do not mutate** 08–21.
8. **Tests:** suite green.

## Out of Scope

- LIVE promotion / live orders  
- Re-optimizing lookback/skip  
- Changing risk limits  
- BAR-001 quality fix (note only)

## Acceptance (Jr)

1. `.venv/bin/python -m pytest tests/execution/ tests/acquisition/ -q --tb=short`
2. `.venv/bin/python -m ruff check src/cryptofactors/execution scripts/`
3. `22_TSMOM_14_0_PAPER_SESSION.json` present; `live_eligible: false`
4. `python3 scripts/check_repo_control.py`

## Stop Condition

After Sr: AWAITING_REVIEW, Next ticket authorized: NONE.
