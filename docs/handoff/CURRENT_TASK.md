# CURRENT_TASK

Ticket: EXP-006
State: AWAITING_REVIEW
Next required actor: Lead Quantitative Finance Researcher/Engineer
Next ticket authorized: NONE

**Reviewer Decision (REVIEW-0196): CHANGES_REQUIRED**

Folds 1–2 `meets_risk`/`is_complete` false because paper `effective_time=2026-04-01` makes `ProspectiveEvaluator` fail before test end; period logs show risk was enforced (max |w|=0.15, gross≤1.0). Artifact gates unusable as written.

## Must fix

1. Derive research OOS `meets_risk_limits` / `is_complete` without depending on paper effective_time (period-log risk + fold completeness), **or** set effective_time ≤ each fold’s first decision and align obs window to the test fold
2. Re-run all folds; rewrite only `21_TSMOM_EXTENDED_OOS.json`
3. Accurate protocol name (train unused → sequential holdout, not expanding selection)
4. `live_eligible: false`; `oos_supports_live_path` from corrected gates only
5. No LIVE; do not mutate 08–20

## Governing documents

- tickets/EXP-006.md (AWAITING_REVIEW)
- docs/reviews/REVIEW-0196_EXP-006_CHANGES_REQUIRED.md

## Acceptance (Jr)

1. .venv/bin/python -m pytest tests/execution/ tests/acquisition/ -q --tb=short
2. .venv/bin/python -m ruff check src/cryptofactors/execution scripts/
3. 21_TSMOM_EXTENDED_OOS.json present with corrected flags
4. python3 scripts/check_repo_control.py
