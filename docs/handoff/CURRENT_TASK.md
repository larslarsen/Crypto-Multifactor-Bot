Ticket: REF-001
State: IN_PROGRESS
Governing documents:
- tickets/REF-001.md
- docs/architecture/01_DATA_ARCHITECTURE.md
- docs/reviews/REF-001_SR_INTEGRITY_FIXES.md
- docs/reviews/REF-001_INTEGRATION.md
- docs/reviews/REVIEW-0016_AUD-001_ACCEPTED.md
Authorized scope: Integrate the in-tree Sr REF-001 integrity-fix source under src/cryptofactors/reference/ per docs/reviews/REF-001_SR_INTEGRITY_FIXES.md. Add regressions, run validation, update integration evidence and change report. Do not begin another ticket.
Required outcome: REF-001 deliverables — stable asset/instrument/venue IDs; bitemporal records (valid-time + system-known-time); alias resolution requiring decision timestamp with effective persisted manual decisions; manual resolution queue; no automatic merge on symbol text; contiguous knowledge-time supersession for aliases and instrument versions; synthetic tests for ticker reuse, redenomination, migration, delisting, and late metadata correction.
Stop condition: After the acceptance commands pass and integration evidence is recorded, commit and stop for review. Do not begin the next ticket.
Next ticket authorized: NONE
