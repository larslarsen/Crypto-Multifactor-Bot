Ticket: REF-001
State: IN_PROGRESS
Authorized scope: Integrate Sr drops REF001_reference_master.zip (v1: store + migration 0006) and REF001_v2_corrections.zip (v2: 9 defect corrections). v2 integrated with Jr fixes for two Sr-omitted helpers (_require_instrument_version, _row_to_ambiguity) and an unused-import removal. Focused regression suite added (tests/reference/test_ref_store.py, 11 tests, all green). Prerequisites satisfied: CAT-001 (asset catalog) and AUD-001 data-audit (ACCEPTED, REVIEW-0016). Acceptance not yet recorded; await reviewer verdict. Next ticket authorized: NONE.
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
- docs/reviews/REF-001_INTEGRATION.md
- docs/reviews/REVIEW-0016_AUD-001_ACCEPTED.md
- docs/reviews/REVIEW-0012_LEG-001_FINAL.md
