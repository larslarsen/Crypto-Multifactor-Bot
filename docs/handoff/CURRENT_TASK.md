# CURRENT_TASK

Ticket: DATA-006
State: AWAITING_REVIEW
Next required actor: Lead Quantitative Finance Researcher/Engineer (reviewer)
Next ticket authorized: NONE

## Governing documents

- tickets/DATA-006.md
- tickets/INFRA-001.md
- research/sprint_004/29_HOLDOUT_RESERVATION.json
- tickets/templates/PRE_REGISTERED_TEST.md

## Status

Sr Dev completed DATA-006 implementation. All source drops, backfill scripts, and 3 artifacts (31–33) are committed. Awaiting reviewer acceptance.

**Jr verification:**
- ✅ pytest tests/acquisition/ tests/ingest/ — 100% PASS
- ✅ ruff — ALL CHECKS PASSED
- ✅ Binance: 258 symbols, 90,276 bars, PASS, 2020-01→2026-07
- ✅ BitMEX: 5 symbols, 32,768 rows, PASS
- ✅ DEX: 2 pools, 356 rows, PASS
- ✅ Pipeline scripts + tests on disk
