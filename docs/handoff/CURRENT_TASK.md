# CURRENT_TASK

Ticket: DEX-002
State: READY
Next required actor: Sr Dev (Strong Model) — multi-provider free DEX OHLCV fan-out
Next ticket authorized: UNIVERSE-004

**Reviewer Decision (Architecture & Ticket Selection):**

DATA-008 ACCEPTED. Binance universe expanded from 23 to 52 symbols (29 added), 70k+ bars, 0 rate-limit incidents. New pinned dataset `ds_c094b7c9b6ba825d0d0585a2c51e03ae5ce0992fac4c7b57dd74ba21f77dfcf8`.

Queue now:
1. **DEX-002** (active) — Multi-provider free DEX OHLCV fan-out
2. **UNIVERSE-004** (next) — Birdeye listings → screen → OHLCV queue

Rules: No Birdeye OHLCV. No LIVE. Screen-prioritize.

## Governing documents

- tickets/DEX-002.md
- tickets/UNIVERSE-004.md
- tickets/DATA-008.md (ACCEPTED)
- tickets/DATA-007.md (ACCEPTED)
- tickets/UNIVERSE-002.md (ACCEPTED)
- research/sprint_004/35_FREE_SOURCE_RATE_LIMIT_MATRIX.json
- research/sprint_004/36_BINANCE_UNIVERSE_EXPANSION.json
- src/cryptofactors/acquisition/free_source_probes.py

## Acceptance (Jr)

per tickets/DEX-002.md
