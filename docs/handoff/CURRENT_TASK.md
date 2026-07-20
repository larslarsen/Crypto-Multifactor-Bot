Ticket: BIN-001
State: IN_PROGRESS
Accepted dependencies: RAW-001 (accepted), MAN-001 (accepted), REF-001 (accepted at b742e8d2a3cf5239b93a9541aa0013589297cad2; REVIEW-0017).
Governing documents:
- tickets/BIN-001.md
- docs/architecture/07_IMPLEMENTATION_ROADMAP.md
- docs/architecture/01_DATA_ARCHITECTURE.md
- docs/reviews/REVIEW-0017_REF-001_ACCEPTED.md
- docs/reviews/REVIEW-0018_BIN-001_CHANGES_REQUIRED.md
- docs/reviews/REVIEW-0019_BIN-001_CHANGES_REQUIRED.md
- docs/reviews/REVIEW-0020_BIN-001_CHANGES_REQUIRED.md
- docs/reviews/REVIEW-0021_BIN-001_INTEGRATION_CHANGES_REQUIRED.md
- docs/reviews/BIN-001_CHANGE_REPORT.md
Authorized scope: Complete the Jr-only integration-evidence remediation in REVIEW-0021. Jr Dev - Hermes may edit focused tests and BIN-001 records, run acceptance gates, and own Git/commit/push. Production source changes and Sr Dev work are not authorized unless a strengthened publication regression exposes a source defect and the reviewer routes it. No migration, architecture, or unrelated product changes.
Required outcome: BIN-001 deliverables — normalize registered Binance archive objects into source-specific typed bars; publish canonical bars only after quality acceptance. Required cases: explicit market type and interval; timestamp unit handling across source eras; UTC interval semantics; quote/base volume units; duplicate and gap handling through quality issues; source object lineage on every output partition; no network access in the normalizer.
Stop condition: After the corrected acceptance commands pass, update the change report, commit and push, then stop for reviewer inspection. Do not begin the next ticket.
Next ticket authorized: NONE
