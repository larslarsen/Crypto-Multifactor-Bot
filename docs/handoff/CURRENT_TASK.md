Ticket: BIN-001
State: IN_PROGRESS
Accepted dependencies: RAW-001 (accepted), MAN-001 (accepted), REF-001 (accepted at b742e8d2a3cf5239b93a9541aa0013589297cad2; REVIEW-0017).
Governing documents:
- tickets/BIN-001.md
- docs/architecture/07_IMPLEMENTATION_ROADMAP.md
- docs/architecture/01_DATA_ARCHITECTURE.md
- docs/reviews/REVIEW-0017_REF-001_ACCEPTED.md
Authorized scope: Activate BIN-001 (Binance archive kline normalizer) as the sole current ticket. Dependencies RAW-001, MAN-001, and REF-001 are accepted. No production-source, migration, architecture, or product-test changes in this control-plane activation.
Required outcome: BIN-001 deliverables — normalize registered Binance archive objects into source-specific typed bars; publish canonical bars only after quality acceptance. Required cases: explicit market type and interval; timestamp unit handling across source eras; UTC interval semantics; quote/base volume units; duplicate and gap handling through quality issues; source object lineage on every output partition; no network access in the normalizer.
Stop condition: After the acceptance commands pass, produce a change report and stop. Do not begin the next ticket.
Next ticket authorized: NONE
