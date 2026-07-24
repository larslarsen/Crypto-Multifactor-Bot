# CURRENT_TASK

Ticket: DATA-010
State: AWAITING_REVIEW
Next required actor: Reviewer (Lead Quant) — switch to strong model for code review
Next ticket authorized: NONE

**Sr rework delivered — key changes:**
- DEX-002 screening fail-closed (all providers consulted; no short-circuit)
- Address validation (`is_valid_pool_address`: EVM 20-byte / Solana base58)
- U50 coverage expanded to 14 symbols (added SOL, XRP, ADA, DOT, FIL, APE, PEPE + others via Solana)
- Token map extended with Solana addresses for previously-missing assets
- DefiLlama screening exercises `coins.llama.fi` endpoint; `produces_ohlcv=False`
- Watermark advance now covers empty/failed providers (advance to end_time)
- `max_pools_per_run` budget control
- Solana address case preserved for case-sensitive lookups

**Known/unresolved:**
- Thresholds still 0/0 (ticket default: 50k/10k)
- `rejected_pools: []`
- 6 Solana pools with 0 records (GeckoTerminal coverage gap for Solana?)
- Some U50 assets still missing (ADA, AVAX, LTC, BCH, DOGE, CRV, SEI, SUI in EVM chains)

Evidence: `research/sprint_004/40_DEX_UNIVERSE_BACKFILL.json` (re-published)

## Governing documents

- tickets/DATA-010.md (AWAITING_REVIEW)
- docs/reviews/REVIEW-0211_RETRO_CODE_REVIEW_DATA007_THROUGH_010.md
- tickets/DEX-002.md (READY — rework pending)
- tickets/DATA-009.md (READY — rework pending)
- tickets/DATA-008.md (READY — rework pending)
- tickets/UNIVERSE-004.md (ACCEPTED)
- tickets/DATA-007.md (ACCEPTED)
