# ARCH-003 — Reference Identity and DEX Raw-Event Spine

**Priority:** P0  
**Status:** READY  
**Dependencies:** ADR-0015 (proposed), ARCH-002 (ACCEPTED)  
**Layer:** architecture / acquisition / reference  
**Architecture:** ADR-0015. **No LIVE. No DEX historical backfill. No factor research.**

## Objective

Implement the four-level reference identity model (asset, token_contract, pool_instrument, venue_listing) defined in ADR-0015. Strip identity resolution out of acquisition scripts. Make universe construction a pure catalog-consumer operation.

## Current State

- Acquisition scripts (`dex_multi_provider_fanout.py`, `backfill_binance_klines.py`, `build_bound_bars.py`) embed identity resolution (ticker → instrument_id mapping) inline.
- `PAPER_TO_INSTRUMENT_ID` and `PAPER_TO_BINANCE_MAP` are used as membership sources in acquisition code, not just as execution adapters.
- `ref_asset` and `ref_instrument` catalog tables exist as schemas but are not populated as the authoritative source for universe membership.
- DEX bar building cannot proceed without resolving which pool → which instrument_id → which asset.

## Reviewer Corrections

REVIEW-0219 records CHANGES REQUIRED. Sr Dev must:

1. Remove fabricated 2017 listing dates; use evidence-backed dates or labeled first-bar proxies.
2. Model asset, token contract, pool legs, venue listing, and canonical integer surrogate separately.
3. Replace global DB access and integer-cast catalog IDs with an explicit resolver.
4. Centralize valid-time plus knowledge-time listing lifecycle logic.
5. Bind experiments to immutable published universe datasets, not mutable SQLite tables.
6. Remove identity resolution from raw acquisition without deleting normalization/publication.
7. Replace mutable symbol-registry membership and preserve case-sensitive Solana addresses.
8. Wire all experiment/paper entrypoints to the new binding.

## Scope

### In scope

1. **ADR-0015 ratification** — merge as accepted architecture decision.

2. **Populate `ref_asset` catalog table** — seed with a static list of known assets (UUID, ticker, name, cmc_id, coingecko_id). One row per unique base asset regardless of chain or venue.

3. **Populate `ref_instrument` for token contracts** — for each asset known to have a DEX presence, insert one row per (chain, contract_address) with `instrument_type='token_contract'`.

4. **Populate `ref_instrument` for DEX pools** — for each DEX pool that exists in staged fan-out data, insert one row with `instrument_type='dex_pool'`. The pool row references the two token_contract rows it trades.

5. **Populate `ref_listing_event`** — for each CEX pair in the existing Binance symbol registry, insert a listing event with `venue='binance'`, `venue_symbol`, `instrument_id` (pool or contract), `listed_at`, and (if known) `delisted_at`.

6. **Strip identity from acquisition scripts** — remove inline `PAPER_TO_INSTRUMENT_ID` lookups from:
   - `dex_multi_provider_fanout.py`
   - `backfill_binance_klines.py`
   - `build_bound_bars.py`
   - `birdeye_screen_queue.py`
   - `fetch_cmc_dead_universe.py`
   
   After stripping, these scripts accept raw bytes and write raw objects / source datasets. They do not resolve instrument_ids.

7. **Build identity adapter layer** — create `ref_identity.py` (or similar) that provides lookup functions:
   - `resolve_instrument_id(venue, venue_symbol, as_of) -> int`
   - `resolve_contract_id(chain, address) -> int`
   - `asset_id_for_instrument(instrument_id) -> int`
   
   These functions read from the catalog tables and are the **only** path to instrument_id resolution.

8. **Update `UniverseBinding` from ARCH-002** — the binding's `universe_at()` now consumes `ref_listing_event` instead of the CMC survivorship CSV. The survivorship logic (birth/death proxy) is preserved but sourced from the catalog rather than from a standalone file.

9. **Tests:** ref_identity resolution round-trips; acquisition scripts with identity removed produce correct raw objects; universe_at returns correct membership for a test date.

### Out of scope

- DEX historical OHLCV backfill (separate ticket after identity is resolved)
- CEX universe expansion beyond existing Binance registry
- New factor research
- Populating Birdeye listing data into the catalog (UNIVERSE-004 remains a queue, not a catalog product)

## Deliverables

1. ADR-0015 merged as accepted
2. `ref_asset`, `ref_instrument`, `ref_listing_event` populated with seed data
3. Acquisition scripts stripped of inline identity resolution
4. `ref_identity.py` adapter module with catalog-backed resolve functions
5. `UniverseBinding` updated to consume `ref_listing_event`
6. Unit tests under `tests/reference/` and updated `tests/universe/`
7. Gap document updated noting ARCH-003 identity work

## Acceptance (Sr Dev Grok Build — code changes only)

1. Identity resolution round-trips for 10 test cases (asset → contract → pool → listing)
2. `backfill_binance_klines.py` dry-run succeeds without referencing `PAPER_TO_INSTRUMENT_ID`
3. `UniverseBinding.universe_at(t)` returns correct membership from catalog for t before and after a known listing event
4. No ticker-based joins exist in acquisition code
5. `ruff check src/cryptofactors/ scripts/` passes

Jr Dev runs integration and tests after source drop.

## Stop Condition

After Sr: AWAITING_REVIEW. Next ticket authorized: NONE (reviewer unlocks next architecture or universe ticket).
