# CURRENT_TASK

Ticket: EXP-003
State: AWAITING_REVIEW
Next required actor: Lead Quantitative Finance Researcher/Engineer (reviewer)
Next ticket authorized: NONE

**Reviewer Decision (Architecture & Ticket Selection):**

PAPER-006 ACCEPTED (REVIEW-0190). Risk enforcement + honest gate land. Risk-compliant real paper **−3.31%** on real as-of (Apr–May 2026) while unconstrained was **+1.37%** with illegal concentration. LIVE still blocked.

Authorizing **EXP-003**:
1. Diagnose unconstrained vs enforced return gap
2. Longer real-window risk-enforced session if data allows
3. Artifacts under research/sprint_004/; `live_eligible: false`

**Policy:** No LIVE.

## Implemented

- Added `scripts/research/diagnose_momts_risk.py` (EXP-003) that:
  - Backfills the 10-name mapped universe over real Binance data (2025-07-01 → 2026-07-23).
  - Runs both unconstrained (single-asset cap disabled) and risk-enforced (0.15 / 1.0) paper sessions.
  - Compares weights, gross leverage, net exposure, and returns per decision.
  - Attributes the return gap to clipping / gross scale / dollar-neutrality drift.
- Extended `scripts/research/backfill_binance_klines.py` with `--report-path` so EXP-003 does not overwrite the PAPER-006 `11_REAL_DATA_PATH_REPORT.json`.
- Added `_CachedAsOfStore` wrapper in the diagnosis script to avoid repeated Parquet reads across the two loops.
- Produced `research/sprint_004/15_MOMTS_RISK_DIAGNOSIS.json` and `16_MOMTS_LONG_SESSION.json`.
- Longer window: 50 weekly decisions (≈12 months) from 2025-08-08 to 2026-07-23.
  - Unconstrained: **−5.28%**
  - Risk-enforced: **−15.36%**
  - Return gap: **+10.08 pp** attributable to the 0.15 single-asset cap and subsequent renormalization.
- Updated `research/sprint_004/experiment_registry.csv` with EXP-003 row.
- `live_eligible: false` in all artifacts; `live_gate_satisfied` computed honestly.
- No LIVE. No live orders.

## Governing documents

- tickets/EXP-003.md (AWAITING_REVIEW)
- tickets/PAPER-006.md (ACCEPTED)
- docs/reviews/REVIEW-0190_PAPER-006_ACCEPTED.md

## Acceptance (Jr)

1. .venv/bin/python -m pytest tests/execution/ tests/acquisition/ -q --tb=short
2. .venv/bin/python -m ruff check src/cryptofactors/execution scripts/
3. 15_MOMTS_RISK_DIAGNOSIS.json present
4. python3 scripts/check_repo_control.py
