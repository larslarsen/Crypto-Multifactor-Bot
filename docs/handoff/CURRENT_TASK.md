# CURRENT_TASK

Ticket: ASOF-002
State: READY
Next required actor: Sr Dev (Grok Build)
Next ticket authorized: NONE

Reviewer decision: Option A — fix CatalogAsOfStore half-open window. One-character fix unblocks all factor computations. BASE-001 resumes after ASOF-002 accepted.

Governing documents:
- tickets/ASOF-002.md (READY)
- tickets/BASE-001.md (BLOCKED, awaiting ASOF-002)
- docs/reviews/REVIEW-0158_BASE-001_REJECTED.md

## Model Note

Sr Dev Grok 4.5 ran out of credits. This ticket assigned to Sr Dev Grok 0.1 (weaker model). Grok 4.5 should review source before acceptance. Do NOT skip strong-model review.

## Sr Dev Prompt

```
Fix ASOF-002: Completed-bar window in observation_eligible.

Bug: src/cryptofactors/catalog/as_of.py:131 uses >= valid_to_us.
Production BAR-001 sets availability_time = period_end, so bars are
ineligible at their exact availability time (decision_time == period_end).

One-character fix: change >= to > at line 131.
This makes the period window [period_start, period_end] inclusive.

Before:
    if decision_time_us >= valid_to_us:
        return False

After:
    if decision_time_us > valid_to_us:
        return False

Verification: test_catalog_asof_raw_store_ref_and_completed_bar_access
should change from 0 rows to 1 row for completed bars.

Files to modify:
- src/cryptofactors/catalog/as_of.py (line 131, one char)

After completion: set status to AWAITING_REVIEW.
```

## Stop condition

Sr Dev produces source, stops for Reviewer. No commits until Reviewer accepts.
