# CURRENT_TASK

Ticket: BASE-001
State: BLOCKED
Next required actor: Reviewer (decision required)
Next ticket authorized: NONE

BASE-001 source rejected again (REVIEW-0158). P1: no production completed-bar access. Raw CatalogAsOfStore returns zero rows for completed bars when availability_time = period_end. Test uses test-only wrapper.

Governing documents:
- tickets/BASE-001.md (BLOCKED)
- docs/reviews/REVIEW-0158_BASE-001_REJECTED.md
- docs/reviews/REVIEW-0157_BASE-001_REJECTED.md
- docs/reviews/REVIEW-0156_BASE-001_REJECTED.md

## Reviewer decision required

Three options for unblocking baseline factors:

A) **Implement completed-bar access in CatalogAsOfStore** — fix the production store to handle completed bars (availability_time = period_end). Production fix.

B) **Create a production CompletedBarAsOf adapter** — add `src/cryptofactors/factors/completed_bar_asof.py` that wraps CatalogAsOfStore for completed-bar semantics.

C) **Document the limitation** — accept the test-only wrapper for now, document that baseline factors require completed-bar semantics that CatalogAsOfStore doesn't support.

No next ticket authorized. No further work on BASE-001 until Reviewer selects option.
