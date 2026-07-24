# CURRENT_TASK

Ticket: DATA-007
State: READY
Next required actor: Sr Dev (Strong Model) — free source & rate-limit probe matrix
Next ticket authorized: DATA-007

**Reviewer Decision (Architecture & Ticket Selection):**

DATA-006 ACCEPTED. Owner direction: free-data-first; multi-API DEX fan-out; Birdeye stays **listings only**; DEX death = low liquidity/volume; prioritize by screen when full universe impossible.

**Ticket set written:**
| ID | Role | Status |
|----|------|--------|
| **DATA-007** | Probe free sources + rate limits + recommended fan-out | **AUTHORIZED / READY** |
| DEX-002 | Multi-provider OHLCV fan-out | DRAFT (after 007) |
| UNIVERSE-004 | Birdeye listings → screen → OHLCV queue + liquidity death | DRAFT |
| DATA-008 | Free CEX expansion (Binance-first) | DRAFT |

**DATA-007 hard rules:** No Birdeye OHLCV. No LIVE. Artifact `35_FREE_SOURCE_RATE_LIMIT_MATRIX.json`.

## Governing documents

- tickets/DATA-007.md
- tickets/DEX-002.md
- tickets/UNIVERSE-004.md
- tickets/DATA-008.md
- tickets/UNIVERSE-002.md
- tickets/DATA-006.md

## Acceptance (Jr)

1. pytest (scoped or full as ticket)
2. ruff
3. 35_FREE_SOURCE_RATE_LIMIT_MATRIX.json present
4. python3 scripts/check_repo_control.py
