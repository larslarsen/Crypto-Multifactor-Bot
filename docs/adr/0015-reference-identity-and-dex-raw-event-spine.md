# ADR 0015 — Reference Identity and DEX Raw-Event Spine

- **Status:** Proposed (pending reviewer decision)
- **Date:** 2026-07-25
- **Supersedes:** implicit ticker-based asset joins in acquisition and universe code

**Review status:** REVIEW-0219 CHANGES REQUIRED. This ADR remains Proposed and is
not an accepted implementation authority until the required corrections are reviewed.

## Required Corrections Before Acceptance

The implementation must use evidence-backed listing dates or labeled first-bar
proxies; separate asset, token contract, pool legs, venue listing, and canonical
integer surrogate; use an explicit resolver rather than global DB access or integer
casts; centralize valid-time and knowledge-time lifecycle logic; bind research to
immutable published universe datasets; preserve normalization/publication while
removing identity resolution from raw acquisition; replace mutable symbol-registry
membership; preserve case-sensitive Solana addresses; and wire every experiment and
paper entrypoint to the new binding.

## Context

1. **Ticker-based identity is ambiguous.**
   - Base asset tickers (`BTC`, `ETH`, `SOL`) collide across chains, wrapped representations,
     and venues. Ticker-level joins between acquisition, bar-building, and universe membership
     silently merge unrelated instruments.
   - `PAPER_TO_INSTRUMENT_ID` and its reverse map conflate symbol semantics: a paper symbol
     such as `XBTUSD` names a *trading pair on a specific venue* but was used as a
     *base-asset key* in acquisition logic.

2. **DEX data requires four distinct identity levels that no existing model captures.**
   - **Asset** — the underlying digital commodity (e.g. Bitcoin). Has no chain, no venue,
     no pool. Immutable reference.
   - **Token contract** — an ERC-20 / SPL / native-l1 address on exactly one chain.
     One asset may have many contracts (wrapped, bridged, native).
   - **Pool instrument** — a specific DEX pool (address, chain, fee tier, provider).
     Trades two token contracts. The atomic tradable entity.
   - **Venue listing** — an exchange's representation of a pair (e.g. Binance `BTCUSDT`).
     May be delisted, suspended, or migrated.

3. **Current code conflates these levels.**
   - `PAPER_TO_BINANCE_MAP` maps a paper symbol → one Binance pair, but paper symbols
     were designed as base-asset keys. When a base asset trades on multiple venues or
     multiple pools, the static map cannot express the relationship.
   - DEX acquisition (`dex_multi_provider_fanout.py`) and the Birdeye listing queue
     (`birdeye_screen_queue.py`) both use ticker strings as asset keys, making it
     impossible to distinguish which chain/contract a bar or event belongs to.

4. **Acquisition currently owns both network I/O and identity resolution.**
   - `fetch_cmc_dead_universe.py` calls the CMC API and writes CSV.
   - `birdeye_screen_queue.py` calls Birdeye API and writes catalog records.
   - `backfill_binance_klines.py` calls Binance REST and writes raw objects.
   - Identity logic (which symbol → which Binance pair, which asset → which pool) is
     embedded inside acquisition scripts instead of being a consumed catalog product.

## Decision

1. **Separate identity into four levels in the reference model.**

   | Level | Identity | Source of Truth | Mutability |
   |-------|----------|----------------|------------|
   | Asset | `asset_id` (UUID or integer) | `ref_asset` catalog table | Immutable after creation |
   | Token contract | `contract_id` = chain + address | `ref_instrument` with `instrument_type='token_contract'` | Immutable after creation |
   | Pool instrument | `pool_id` = chain + pool_address + fee_tier | `ref_instrument` with `instrument_type='dex_pool'` | Immutable after creation |
   | Venue listing | `listing_id` = venue + venue_symbol | `ref_listing_event` catalog table | Time-bound (birth/death events) |

2. **Acquisition owns networking and raw bytes only.**
   - Acquisition scripts fetch bytes from APIs and write raw objects / source datasets.
   - They do **not** resolve identities, map symbols, or decide which instruments belong
     to a universe.
   - Identity resolution is a **catalog-consumer** concern, not a **producer** concern.

3. **Universe construction consumes immutable catalog datasets.**
   - `ref_asset`, `ref_instrument`, `ref_listing_event` are populated by dedicated
     reference-data scripts (not acquisition scripts).
   - A universe dataset is a snapshot of `ref_listing_event` + `ref_instrument` filtered
     by time, venue, and minimal quality criteria.
   - No ticker-based joins between acquisition output and universe membership.

4. **Execution maps are read-only adapters.**
   - `PAPER_TO_INSTRUMENT_ID` and related maps become **adapter-only** — they translate
     between the agent's internal paper-symbol namespace and catalog-resolved
     `instrument_id` values. They are **never** the source of membership.
   - A paper session's universe is always `binding.universe_at(t)`, not `list(PAPER_TO_INSTRUMENT_ID.keys())`.

5. **DEX raw-event spine.**
   - All DEX data (OHLCV, swaps, liquidity snapshots) is ingested as **raw events**
     keyed by `pool_id` (chain + pool_address + fee_tier).
   - Bar building consumes raw events and produces `market_bars` with `instrument_id`
     corresponding to the pool instrument.
   - No DEX bar dataset is published without a corresponding `ref_instrument` row for
     every `instrument_id` it references.

## Consequences

- **Positive:** Asset joins become unambiguous. A bar row for Uniswap WETH/USDC on
  Ethereum mainnet and a bar row for Binance ETHUSDT are distinguishable at the
  identity level and can be correctly handled by research.
- **Positive:** Acquisition scripts become simpler — they fetch bytes and write them.
  Identity mapping moves to reference-data scripts that are easier to audit and test.
- **Negative:** Several existing scripts (`dex_multi_provider_fanout.py`,
  `backfill_binance_klines.py`, `build_bound_bars.py`) need refactoring to stop
  doing identity resolution inline.
- **Negative:** The reference-data catalog tables (`ref_asset`, `ref_instrument`,
  `ref_listing_event`) need to be populated before DEX bar building can proceed.
  This is a prerequisite, not a parallel workstream.
- **Research scope reduced:** Until identity is clean, any experiment mixing CEX and
  DEX data has unquantifiable cross-identity contamination risk.
