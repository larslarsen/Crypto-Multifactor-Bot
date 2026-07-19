Ticket: REF-001
State: IN_PROGRESS
Authorized scope: Activate REF-001 (point-in-time asset and instrument master) as the sole current ticket. Prerequisites satisfied: CAT-001 (asset catalog) by the accepted catalog work, and AUD-001 data-audit findings (ACCEPTED, REVIEW-0016 at `5fac3ac20f4c88074207f795aef3b5f7d6078f5b`). No production-source, migration, schema, or test changes in this control-plane activation.
Required outcome: REF-001 deliverables — stable asset/instrument/venue IDs; bitemporal records (valid-time + system-known-time); alias resolution requiring decision timestamp; manual resolution queue; no automatic merge on symbol text; synthetic tests for ticker reuse, redenomination, migration, delisting, late metadata correction.
Stop condition: After the acceptance commands pass, produce a change report and stop. Do not begin the next ticket.
Next ticket authorized: NONE
Governing documents:
- tickets/REF-001.md
- tickets/CAT-001.md
- tickets/AUD-001.md
- tickets/LEG-001.md
- tickets/MAN-001.md
- docs/architecture/08_LEGACY_MIGRATION_PLAN.md
- docs/reviews/AUD-001_INTEGRATION.md
- docs/reviews/REVIEW-0016_AUD-001_ACCEPTED.md
- docs/reviews/REVIEW-0012_LEG-001_FINAL.md
