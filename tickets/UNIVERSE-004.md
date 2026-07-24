# UNIVERSE-004 — Birdeye Listings → Screen → OHLCV Queue + Liquidity Death

**Priority:** P1  
**Status:** ACCEPTED
**Next:** NONE  
**Dependencies:** UNIVERSE-002 (ACCEPTED), DATA-007 (ACCEPTED), DEX-002 (ACCEPTED)  
**Layer:** universe  
**Architecture:** events drive bar requests. **No Birdeye OHLCV.**

## Objective

Use **Birdeye new-listing events** (free key, listings only) as the top of funnel. Apply **screening criteria** (liquidity, volume, chain allowlist, etc.). Enqueue survivors for **DEX-002 OHLCV** providers. Define **pragmatic DEX death** as sustained lack of liquidity/volume (not an official delist message).

## Scope (summary)

1. Forward listing ingest stays on Birdeye listing endpoints only.
2. Screen config: thresholds + chains; deterministic, versioned.
3. Output: `ohlcv_request_queue` (or equivalent dataset) of `(chain, address/pool, reason, enqueued_at)`.
4. Death/inactive state from pool stats / OHLCV-derived activity (from DEX-002 sources), labeled non-survivorship-free.
5. As-of membership: listed ∧ not dead_by_liquidity_rule.

## Hard constraints

- Never spend Birdeye CU on OHLCV.
- Death rule is pragmatic research definition; document in artifact.

## Stop Condition

After Sr: AWAITING_REVIEW, Next NONE.
