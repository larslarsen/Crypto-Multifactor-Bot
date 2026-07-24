# CURRENT_TASK

Ticket: DATA-010
State: READY
Next required actor: Sr Dev (Strong Model) — fix review issues and re-run
Next ticket authorized: NONE

**Review Findings (blocking):**
1. Incomplete U50 universe — 9/23 symbols only (SOL, XRP, ADA, AVAX, DOT, LTC, BCH, DOGE, CRV, APE, FIL, SUI, SEI, PEPE missing). Need ≥1 valid pool per resolvable asset.
2. Invalid addresses — 3 records have 66-char hex (32-byte) not 20-byte EVM addresses; caused DexScreener 400s. Validate & reject non-20-byte before enqueue.
3. Thresholds — ticket says 50k/10k; report ran at 5k/1k. Run at defaults or document.
4. Zero rejected pools recorded — must include unresolved/rejected assets with reasons.
5. DefiLlama unused — 0 requests in real run.
6. Re-publish report + dataset after fixes.

## Governing documents

- tickets/DATA-010.md (READY)
