Ticket: LEG-001
State: IN_PROGRESS
Authorized scope: Integrate Sr acceptance-fix production drop (legacy_local.py v1.2.1); add or extend focused tests for the four acceptance blockers listed in tickets/LEG-001.md; run acceptance commands; stop for review.
Required outcome: Production scanner satisfies path-identity, zero-byte size, output-subtree exclusion, and bounded iteration/streaming-duplicate invariants; tests encode those blockers; acceptance commands green.
Stop condition: After acceptance commands pass, produce a short change report under docs/reviews/ (or append LEG-001_INTEGRATION.md) and stop. Do not begin the next ticket. Do not push.
Next ticket authorized: NONE
Governing documents:
- tickets/LEG-001.md
- tickets/RAW-001.md
- docs/architecture/08_LEGACY_MIGRATION_PLAN.md
- docs/reviews/REVIEW-0009_RAW-001_FINAL.md
- docs/reviews/REVIEW-0011_MAN-001_FINAL.md
- docs/reviews/LEG-001_INTEGRATION.md
- docs/reviews/LEG-001_SR_ACCEPTANCE_FIXES.md
