# CURRENT_TASK

Ticket: NULL-001
State: BLOCKED
Next required actor: Sr Dev (corrections required)
Next ticket authorized: NONE

NULL-001 source rejected again (REVIEW-0153). P1: test scope violates ticket (20 assets/220 days vs 100/365). P1: Sharpe tolerance widened from ±0.5 to 1.0 without ticket update. P2: daily IR check adds no independent constraint.

Governing documents:
- tickets/NULL-001.md (BLOCKED)
- docs/reviews/REVIEW-0153_NULL-001_REJECTED.md
- docs/reviews/REVIEW-0152_NULL-001_REJECTED.md
- docs/reviews/REVIEW-0151_NULL-001_REJECTED.md
- docs/reviews/REVIEW-0150_UNIVERSE-001_REJECTED.md
- docs/reviews/REVIEW-0148_EXP-001_ACCEPTED.md

## Sr Dev Correction Prompt

```
Correct NULL-001 source per REVIEW-0153 findings.

P1 — Test scope violates ticket:
- tests/test_null_factor.py:66-68 uses 20 assets / 220 days.
- Ticket NULL-001 requires 100 assets / 365 days.
- Update test parameters to match ticket.

P1 — Sharpe tolerance widened:
- tests/test_null_factor.py:72 sets _MEAN_SHARPE_TOL = 1.0.
- Ticket specifies ±0.5.
- Restore tolerance to ±0.5 or update ticket with reviewer approval.

P2 — Daily IR check misleading:
- tests/test_null_factor.py:74 sets _MEAN_DAILY_IR_TOL = 0.12.
- 0.12 daily IR annualizes to Sharpe ~2.29, which is looser than 1.0.
- Remove the IR check or document what it actually validates.

Files to modify:
- tests/test_null_factor.py (primary)
- tickets/NULL-001.md (if tolerance needs updating)

Acceptance:
1. All tests pass (pytest, ruff, mypy)
2. Test parameters match ticket (100 assets, 365 days, ±0.5 Sharpe)
3. check_repo_control.py PASS

After completion: set status to AWAITING_REVIEW.
```

## Stop condition

Sr Dev produces corrected source, stops for Reviewer. No commits until Reviewer accepts.
