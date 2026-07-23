# ADR 0012 — CoinMarketCap Survivorship Backfill & Graveyard Ingestion

- **Status:** Accepted — AWARE-LEVEL PROXY AUTHORITY
- **Date:** 2026-07-22

## Context

The system requires a historical dead-coin universe to mitigate survivorship bias (DF-08). Forward-only DEX listing feeds (such as Birdeye / UNIVERSE-002) cannot reconstruct pre-ingestion dead assets on centralized exchanges (CEXs).

CoinMarketCap maintains historical records for inactive/dead coins via website back-end endpoints (`data-api/v1/cryptocurrency/map?listing_status=inactive` and `data-api/v3/cryptocurrency/detail?id=<id>`).

## Decision

1. **One-Shot Backfill:** Authorize `scripts/research/fetch_cmc_dead_universe.py` and `src/cryptofactors/universe/cmc_survivorship.py` to ingest the CMC inactive coin graveyard as a one-shot historical backfill for the CEX side.
2. **Unofficial Endpoint Risk & Boundary:** The `data-api` endpoint is an undocumented web back-end without SLA or stability guarantees. It MUST NOT be wired as a recurring live dependency.
3. **Date Semantics & Provenance Labeling:**
   - `dateAdded` / `dateLaunched` serve as `birth_date` proxies (point-in-time membership start).
   - `latestUpdateTime` serves as `death_proxy_date` (the time CMC ceased tracking updates). It carries NO final tradable price and NO failure cause.
   - Every registry row MUST explicitly retain provenance labels: `death_date_is_proxy = True` and `source = "cmc_data_api_unofficial"`. Downstream consumers must never launder proxy dates as authoritative exchange delisting times.
   - **Authority level:** Accepted at **Aware-level** — sufficient for research membership queries but NOT authoritative for final-price or failure-cause analysis. Full survivorship-free authority remains open.
4. **DF-08 Scope & Boundary:** This backfill satisfies gap G08 (reconstruction of historical membership) and materially improves G06 (delisted coverage). However, DF-08 remains partially open due to the lack of final tradable prices and failure-cause classifications.

## Consequences

- The historical CEX dead-coin universe is accessible for point-in-time research and portfolio simulations.
- Proxy dates are strictly labeled and isolated from authoritative delisting data.
- The un-slated web endpoint is confined to a one-shot ingestion process.
