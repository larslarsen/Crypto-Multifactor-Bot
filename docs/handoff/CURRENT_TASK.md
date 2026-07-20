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
- docs/reviews/REVIEW-0022_BIN-001_INTEGRATION_CHANGES_REQUIRED.md
- docs/reviews/REVIEW-0023_BIN-001_CHANGES_REQUIRED.md
- docs/reviews/BIN-001_CHANGE_REPORT.md
Authorized scope: Complete the role-scoped remediation in REVIEW-0023. Sr Dev - Grok Build first edits only `src/cryptofactors/ingest/binance.py` to make the returned plan MAN-001-valid and reproducibly identified. Jr Dev - Hermes then owns integration, focused test corrections, records, acceptance gates, Git, commit, and push. No migration, architecture, or unrelated product changes.
Required outcome: BIN-001 deliverables — normalize registered Binance archive objects into source-specific typed bars; publish canonical bars only after quality acceptance. Required cases: explicit market type and interval; timestamp unit handling across source eras; UTC interval semantics; quote/base volume units; duplicate and gap handling through quality issues; source object lineage on every output partition; no network access in the normalizer.
Stop condition: After the corrected acceptance commands pass, update the change report, commit and push, then stop for reviewer inspection. Do not begin the next ticket.
Next ticket authorized: NONE
