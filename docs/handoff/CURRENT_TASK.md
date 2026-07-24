# CURRENT_TASK

Ticket: DATA-007
State: ACCEPTED
Next required actor: Reviewer (Lead Quant) — authorize next ticket
Next ticket authorized: NONE

**Reviewer Decision (Architecture & Ticket Selection):**

DATA-007 ACCEPTED. Free-source rate-limit probe complete. 6 sources probed:
- **GeckoTerminal** (dex_ohlcv, ~180d, 6 req/min) — primary OHLCV
- **DexScreener** (pool_stats, 24h only, 300 req/min) — screening
- **DefiLlama** (pool_stats, full history, 2 req/sec) — liquidity/yield screening
- **Binance** (cex_bars, full history, 1200 req/min) — primary CEX
- **BitMEX** (funding, full history, 120 req/min) — funding
- **Birdeye** (dex_listings only, 100 req/min) — listings only

Estimated capacity: ~720 DEX pools/day, ~3,000 listings/day, ~20k CEX symbols/day.

Matrix artifact: `research/sprint_004/35_FREE_SOURCE_RATE_LIMIT_MATRIX.json`

Next moves (draft tickets ready):
| ID | Role | Priority |
|----|------|----------|
| DEX-002 | Multi-provider free OHLCV fan-out (Gecko + DexScreener + DefiLlama) | P0 |
| UNIVERSE-004 | Birdeye listings → screen → OHLCV queue + liquidity death | P1 |
| DATA-008 | Free CEX expansion (Binance-first) | P1 |

## Governing documents

- tickets/DATA-007.md
- tickets/DEX-002.md
- tickets/UNIVERSE-004.md
- tickets/DATA-008.md
- tickets/UNIVERSE-002.md
- tickets/DATA-006.md
- research/sprint_004/35_FREE_SOURCE_RATE_LIMIT_MATRIX.json
- src/cryptofactors/acquisition/free_source_probes.py

## Acceptance (Jr)

1. pytest — 21 passed
2. ruff — All checks passed
3. 35_FREE_SOURCE_RATE_LIMIT_MATRIX.json — present (6 sources, recommended_fanout, capacity)
4. scripts/check_repo_control.py — PASS
