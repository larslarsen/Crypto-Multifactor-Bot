# ADR 0013 — Birdeye DEX New-Listing Event Feed Ingestion

- **Status:** Accepted
- **Date:** 2026-07-23

## Context

The repository's universe definition covers CEX instruments via UNIVERSE-001 (CoinGecko) and historical CEX dead coins via UNIVERSE-003 (CoinMarketCap). Low-cap and DEX token listings are absent from CEX sources.

Birdeye Data Services API provides forward-only token creation/listing events (`/defi/v2/tokens/new_listing`) on Solana and other DEX chains.

## Decision

1. **Ingest Forward Listing Events Only:** Implement `src/cryptofactors/universe/birdeye_listings.py` to ingest DEX token listing events from `GET /defi/v2/tokens/new_listing`.
2. **Hard Guard Against Bar / OHLCV Endpoint Usage:** The module MUST NEVER request or construct OHLCV/bar endpoints (such as `/ohlcv`, `/history`, or `/kline`). Bar ingestion is strictly isolated to BAR-001 (CEX).
3. **Non-Survivorship-Free Labeling:** Birdeye supplies listing events but no delisting or token-death feed. Consequently, DEX listing streams are **NOT survivorship-free**. Every row produced by this provider MUST explicitly record `survivorship_free = False` and `source = "birdeye_new_listing"`.
4. **Credit Unit (CU) Budget Compliance:** The poller uses the `/defi/v2/tokens/new_listing` endpoint only, operating well within the 30,000 CU/month Standard tier limit (~1–3 CU/call at 5–10 minute polling intervals).

## Consequences

- Point-in-time DEX token listing events are available for forward membership queries (`universe_at` and `universe_events_since`).
- Non-survivorship-free status is explicitly declared on every record to prevent invalid survivorship assumptions in DEX factor research.
- Birdeye API credit budget is preserved by forbidding OHLCV bar endpoints.
