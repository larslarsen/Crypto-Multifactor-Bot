# CURRENT_TASK

Ticket: UNIVERSE-004
State: READY
Next required actor: Sr Dev (Strong Model) — Birdeye listings → screen → OHLCV queue + liquidity death
Next ticket authorized: NONE

**Reviewer Decision (Architecture & Ticket Selection):**

DEX-002 ACCEPTED. Multi-provider free DEX OHLCV fan-out implemented: GeckoTerminal primary, DexScreener/DefiLlama secondary, token-bucket rate limiters, merge/dedupe, screening gate, pragmatic death. 357 records across 2 Arbitrum pools, 0 rate-limit incidents.

Queue now:
1. **UNIVERSE-004** (active) — Birdeye listings → screen → OHLCV queue + liquidity death
2. (next TBD)

Rules: No Birdeye OHLCV. No LIVE. Screen-prioritize.

## Governing documents

- tickets/UNIVERSE-004.md
- tickets/DEX-002.md (ACCEPTED)
- tickets/DATA-008.md (ACCEPTED)
- tickets/DATA-007.md (ACCEPTED)
- tickets/UNIVERSE-002.md (ACCEPTED)
- research/sprint_004/35_FREE_SOURCE_RATE_LIMIT_MATRIX.json
- research/sprint_004/36_BINANCE_UNIVERSE_EXPANSION.json
- research/sprint_004/37_DEX_MULTI_PROVIDER_FANOUT.json
- src/cryptofactors/ingest/dex_fanout.py

## Acceptance (Jr)

per tickets/UNIVERSE-004.md
