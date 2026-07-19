Ticket: LEG-001
State: ACCEPTED
Authorized scope: Integrate Sr acceptance-fix production drop (legacy_local.py v1.2.1 -> v1.2.2 merge-key fix); add focused tests for the four acceptance blockers and a strengthened merge-key regression (15 tests total); run acceptance commands; record final acceptance.
Required outcome: Production scanner (v1.2.2) satisfies path-identity, zero-byte size, output-subtree exclusion, bounded iteration/streaming-duplicate, and binary-key merge-order invariants; tests encode those; acceptance commands green.
Stop condition: LEG-001 accepted at 009dd112e7dd722e9075467faa594af944983c56; final review recorded; control plane synced. Do not begin the next ticket.
Next ticket authorized: NONE
Governing documents:
- tickets/LEG-001.md
- tickets/RAW-001.md
- docs/architecture/08_LEGACY_MIGRATION_PLAN.md
- docs/reviews/REVIEW-0009_RAW-001_FINAL.md
- docs/reviews/REVIEW-0011_MAN-001_FINAL.md
- docs/reviews/LEG-001_INTEGRATION.md
- docs/reviews/LEG-001_SR_ACCEPTANCE_FIXES.md
- docs/reviews/REVIEW-0012_LEG-001_FINAL.md
