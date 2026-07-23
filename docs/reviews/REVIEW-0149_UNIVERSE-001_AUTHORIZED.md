# REVIEW-0149 — UNIVERSE-001 AUTHORIZED (CoinGecko Survivorship-Free Universe)

**Authorized ticket:** UNIVERSE-001
**Priority:** P0 (research substrate)
**Gate role:** BLOCKING_FOR_SURVIVORSHIP_FREE_UNIVERSE
**Date:** 2026-07-22
**Next required actor:** Sr Dev (source) then Jr Dev (integration)

## Authorization

After ASOF-001, SPLIT-001, LABEL-001, and EXP-001 acceptance, authorize the CoinGecko universe provider (Implementation Sequence #11).

This unblocks #15 (costed portfolio simulation) and enables experiment #18 (null/noise factor test).

Objective: Provide point-in-time universe of crypto instruments using CoinGecko free tier. Include active + delisted coins. Use existing BAR-001 price data.

## Required Contract
- `CoinGeckoUniverseProvider` fetches full coin list from CoinGecko `/coins/list?status=inactive`
- `universe_at(decision_time)` returns instruments listed at decision_time
- Store universe snapshots in control catalog
- Deterministic, fail-closed

## Scope
- New module under `src/cryptofactors/universe/`
- CoinGecko free tier only (365 days OHLCV)
- Universe membership only; prices from BAR-001

## Out of Scope
- Full historical OHLCV (requires paid plan)
- Factor computation, portfolio simulation, new data sources

## Next
1. Sr produces source drop. Stop for reviewer.
2. Jr integrates + tests + gates. AWAITING_REVIEW.
3. No next ticket authorized.
