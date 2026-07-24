# CURRENT_TASK

Ticket: DATA-008
State: READY
Next required actor: Sr Dev (Strong Model) — free Binance universe expansion
Next ticket authorized: DEX-002

**Reviewer Decision (Architecture & Ticket Selection):**

DATA-007 ACCEPTED. All three expansion tickets authorized. Order:
1. **DATA-008** (active) — Free Binance universe expansion
2. **DEX-002** (next) — Multi-provider free DEX OHLCV fan-out
3. **UNIVERSE-004** (after DEX-002) — Birdeye listings → screen → OHLCV queue

Rules: No Birdeye OHLCV. No LIVE. Screen-prioritize, not "all listings."

## Governing documents

- tickets/DATA-008.md
- tickets/DEX-002.md
- tickets/UNIVERSE-004.md
- tickets/DATA-007.md (ACCEPTED)
- tickets/DATA-006.md (ACCEPTED)
- tickets/UNIVERSE-002.md (ACCEPTED)
- research/sprint_004/35_FREE_SOURCE_RATE_LIMIT_MATRIX.json
- src/cryptofactors/acquisition/free_source_probes.py

## Acceptance (Jr)

per tickets/DATA-008.md
