# CURRENT_TASK

Ticket: FUND-001
State: AWAITING_REVIEW
Next ticket authorized: NONE
Next required actor: Reviewer

Accepted dependencies: RAW-001/002, MAN-001, REF-001, AUD-003, RES-001; Binance funding evidence
from Sprint 003. FX-002 remains accepted with no viable primary source.
Governing documents:
- tickets/FUND-001.md
- docs/architecture/01_DATA_ARCHITECTURE.md
- docs/architecture/02_DATA_SOURCE_PLAN.md
- docs/architecture/07_IMPLEMENTATION_ROADMAP.md
- docs/handoff/IMPLEMENTATION_SEQUENCE.md
- research/sprint_003/sources/binance.md
- research/sprint_003/02_SOURCE_OBJECT_INVENTORY.csv
- research/sprint_003/08_RESEARCH_DATA_DECISIONS.csv
- schemas/funding_cashflow.schema.json
- src/cryptofactors/reference/models.py
- src/cryptofactors/market/bars.py
- docs/reviews/REVIEW-0090_FUND-001_READINESS_AUTHORIZED.md
- docs/reviews/FUND-001_JR_READINESS_TASK.md
- docs/reviews/FUND-001_READINESS_REPORT.md
- research/fund_001/source_semantics_matrix.csv
- research/fund_001/platform_contract_matrix.csv

## Authorized work read-only

Readiness-only analysis accepted; recommendation `SOURCE_EVIDENCE_REQUIRED`. No provider calls,
production implementation, schema, migration, ADR, factor, or USD-conversion work is authorized.

## Stop condition

Return control to Reviewer. Retain `Next ticket authorized: NONE`. Do not begin implementation or another ticket.
