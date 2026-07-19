Ticket: AUD-001
State: IN_PROGRESS
Authorized scope: Implement the schema and coverage profiler (bounded sampling + streaming full-pass modes; inferred physical schema with explicit uncertainty; row counts, timestamp min/max, nulls, duplicates, monotonicity, frequency/gaps; numeric ranges and impossible OHLC checks; Parquet/JSON report plus manifest; quality issues surfaced, not silently repaired).
Required outcome: Profiler satisfies AUD-001 deliverables; the accepted `source_audit` toolkit (AUD-002/AUD-003) does NOT count as AUD-001 completion. Acceptance commands green.
Stop condition: After acceptance commands pass, produce a change report and stop. Do not begin the next ticket.
Next ticket authorized: NONE
Governing documents:
- tickets/AUD-001.md
- tickets/LEG-001.md
- tickets/MAN-001.md
- docs/architecture/08_LEGACY_MIGRATION_PLAN.md
- docs/reviews/REVIEW-0012_LEG-001_FINAL.md
- docs/reviews/REVIEW-0005_AUD-001_TOOLKIT_CHANGES_REQUIRED.md
- docs/reviews/AUD-001_INTEGRATION.md
