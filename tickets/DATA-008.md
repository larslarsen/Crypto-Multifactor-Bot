# DATA-008 — Free CEX Universe Expansion (Binance-first)

**Priority:** P1  
**Status:** DRAFT (can authorize after DATA-007 or in parallel once probe confirms Binance headroom)  
**Dependencies:** DATA-006, DATA-007 (recommended)  
**Layer:** acquisition / bars  
**Architecture:** free Binance REST + watermarks. **No LIVE.**

## Objective

Expand spot bar universe/history under **free** Binance rate limits using DATA-007 capacity estimates. Prioritize symbols by screening criteria (liquidity/volume), not “all listings at once.”

## Scope (summary)

1. Symbol priority list from screen (volume/liquidity).
2. Incremental backfill with watermarks; multi-day safe.
3. Optional 2017→2020 deepen for majors if probe allows.
4. Report: symbols added, span, rate-limit incidents, pin canonical dataset id.

## Stop Condition

After Sr: AWAITING_REVIEW, Next NONE.
