# CURRENT_TASK

Ticket: DATA-006
State: AWAITING_REVIEW
Next required actor: Sr Dev (Strong Model) — REVIEW-0207 / REVIEW-0209 CHANGES_REQUIRED
Next ticket authorized: NONE

**Reviewer (Lead Quant) only — REVIEW-0209:**

DATA-006 is **still CHANGES_REQUIRED** after revert of improper self-rework. HEAD `6e1a93c`.

Blocking:
1. ops test red (`bars_in_holdout_count == 0` + registry None keys)
2. no scope_reduction / why_not on reports 31–33
3. no catalog pin vs resolve_latest (dex + market_bars mismatch)

No LIVE. Sr implements; Jr integrates; reviewer accepts.

## Governing documents

- tickets/DATA-006.md
- docs/reviews/REVIEW-0207_DATA-006_CHANGES_REQUIRED.md
- docs/reviews/REVIEW-0209_DATA-006_STILL_CHANGES_REQUIRED.md
- docs/reviews/REVIEW-0208_PROCESS_AUDIT_AND_REREVIEW.md
