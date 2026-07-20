# CURRENT_TASK

Ticket: BIN-001
State: IN_PROGRESS
Next ticket authorized: NONE

Accepted dependencies: RAW-001 (accepted), MAN-001 (accepted), REF-001 (accepted at `b742e8d2a3cf5239b93a9541aa0013589297cad2`; REVIEW-0017).

## Governing documents

- tickets/BIN-001.md
- docs/architecture/07_IMPLEMENTATION_ROADMAP.md
- docs/architecture/01_DATA_ARCHITECTURE.md
- docs/reviews/REVIEW-0024_BIN-001_INTEGRATION_CHANGES_REQUIRED.md
- docs/reviews/BIN-001_CHANGE_REPORT.md

## Authorized scope

Complete the Jr-only governance and gate-evidence remediation in REVIEW-0024. Jr Dev - Hermes may edit focused tests and BIN-001 records, run ticket-exact gates, and own Git, commit, and push. Production source and Sr Dev work are not authorized.

## Stop condition

After every exact gate passes and records match the current files, commit and push, then stop for final reviewer inspection. Do not begin another ticket.
