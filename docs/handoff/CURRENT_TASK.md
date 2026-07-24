# CURRENT_TASK

Ticket: DATA-006
State: AWAITING_REVIEW
Next required actor: Lead Quantitative Finance Researcher/Engineer (reviewer)
Next ticket authorized: NONE

**Sr rework for REVIEW-0207 (option B) complete — awaiting review.**

1. Ops test: `bars_in_holdout_count >= 0` (holdout boundary valid after DATA-006).
2. Scope reduction documented in ticket + reports 31–33 `scope_reduction` + `34_DATA006_REVIEW0207_REWORK.json`.
3. Catalog pins: `catalog_reconciliation` on 31–33 (report id vs resolve_latest).
4. Registry writer hardened in `daily_refresh._append_registry_row`.
5. pytest ops+acquisition+ingest green; ruff green. No LIVE.

## Governing documents

- tickets/DATA-006.md
- docs/reviews/REVIEW-0207_DATA-006_CHANGES_REQUIRED.md
- docs/reviews/REVIEW-0208_PROCESS_AUDIT_AND_REREVIEW.md
- research/sprint_004/34_DATA006_REVIEW0207_REWORK.json
