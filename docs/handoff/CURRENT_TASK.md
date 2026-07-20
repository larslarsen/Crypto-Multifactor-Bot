Ticket: BIN-001
State: IN_PROGRESS
Accepted dependencies: RAW-001 (accepted), MAN-001 (accepted), REF-001 (accepted at b742e8d2a3cf5239b93a9541aa0013589297cad2; REVIEW-0017).
Governing documents:
- tickets/BIN-001.md
- docs/architecture/07_IMPLEMENTATION_ROADMAP.md
- docs/architecture/01_DATA_ARCHITECTURE.md
- docs/reviews/REVIEW-0017_REF-001_ACCEPTED.md
- docs/reviews/REVIEW-0018_BIN-001_CHANGES_REQUIRED.md
- docs/reviews/BIN-001_CHANGE_REPORT.md
Authorized scope: Integrate Sr Dev — Hermes in-tree BIN-001 normalizer drop; add focused regressions; run acceptance gates; record REVIEW-0018 CHANGES_REQUIRED for missing duplicate/gap detection. No production-source, migration, architecture, or product-test changes beyond integrating the Sr drop.
Required outcome: BIN-001 deliverables — normalize registered Binance archive objects into source-specific typed bars; publish canonical bars only after quality acceptance. Required cases: explicit market type and interval; timestamp unit handling across source eras; UTC interval semantics; quote/base volume units; duplicate and gap handling through quality issues; source object lineage on every output partition; no network access in the normalizer.
Stop condition: After the acceptance commands pass, produce a change report and stop. Do not begin the next ticket.
Next ticket authorized: NONE
