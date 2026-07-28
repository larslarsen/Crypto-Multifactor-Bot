# ADR-0015: Data-First DEX Research Substrate

**Status:** ACCEPTED
**Date:** 2026-07-28
**Governing ticket:** DEX-003
**Authority:** Lead Quantitative Finance Researcher/Engineer, Max architecture pass

## Context

The existing DEX path starts from pools visible to current web APIs, screens them using
current liquidity and volume, and acquires at most the recent GeckoTerminal OHLCV
window. That path is useful for operational snapshots and source cross-checks, but it
cannot support historical factor research:

- pools that disappeared before discovery are absent;
- current screening selects survivors using future information;
- historical liquidity is unavailable from the admitted web-API sources;
- the canonical DEX snapshot is not bound to token orientation or a point-in-time
  membership series;
- no accepted adapter connects DEX observations to the factor and experiment layers.

Running an experiment before closing those data gaps repeats the invalid order that
previously allowed research to precede survivorship-correct data. DEX data authority,
coverage, point-in-time membership, and quality must be accepted before any DEX factor
is designed or executed.

## Decision

### 1. Complete bounded venue before multi-venue breadth

The first research-authoritative DEX domain is:

- Ethereum mainnet;
- the canonical Uniswap V2 factory;
- every factory-created pair from deployment block 10,000,835 through a pinned,
  finalized cutoff;
- the research price panel is the complete subset where exactly one side is an
  accepted stable quote token (initially USDC or USDT).

This is not a sample of current high-liquidity pools. It is a census of a declared
venue/protocol domain, including inactive, illiquid, failed, and revived pools. Other
protocols and chains are added only as separate complete domains after this one passes.

### 2. On-chain events are primary authority

Canonical research data must be reconstructed from preserved Ethereum data:

1. Factory `PairCreated` logs establish pool identity, token addresses, and birth.
2. Pair `Swap` logs establish trade prices and stable-quote volume.
3. Pair `Sync` logs establish reserves and direct stable-quote liquidity.
4. Token metadata calls establish decimals; symbols are labels and never identity.
5. Block headers bind every event to canonical block number, hash, and timestamp.

The existing DATA-012 PairCreated ingestor is the foundation. GeckoTerminal,
DexScreener, DefiLlama, and Birdeye are secondary cross-check or prospective monitoring
sources only. They cannot define historical membership, death, price history, or
research coverage.

Every JSON-RPC response, request, receipt, and block dependency is retained through the
raw-object layer. Acquisition must be chunked, resumable, and fail closed on provider
limits, malformed responses, unresolved ranges, or source disagreement.

PairCreated ordinal reconciliation can prove the factory census, but Swap and Sync
events have no equivalent global counter. Their completeness therefore requires either
count-and-identity agreement for every block chunk from two independent RPC providers,
or receipt-level reconstruction from canonical blocks. One provider's successful
`eth_getLogs` response is not sufficient authority because silent result truncation
would otherwise be indistinguishable from an inactive pool.

### 3. Blockchain temporal semantics

Canonical event records carry three distinct times:

- `event_time`: timestamp of the block containing the event;
- `source_available_at`: `event_time + 24 hours`, a conservative deterministic
  finality/publication lag for historical research;
- `retrieved_at`: when this repository acquired the source response.

The historical availability rule applies only to finalized, append-only Ethereum event
data whose block hash and log identity are verified. Mutable web API observations keep
local acquisition time as their availability time. Raw acquisition records are never
rewritten to pretend they were retrieved historically.

Research decisions at time `t` may use only events with `source_available_at <= t`.
The one-day lag also prevents same-day close information from entering that day's
decision.

### 4. Canonical data products

DEX-003 must publish immutable, lineage-closed datasets for:

1. `dex_pool_registry`: chain, protocol, factory, pool address, token0, token1,
   creation block, event time, source availability, and raw identities.
2. `dex_pool_events`: normalized PairCreated, Swap, and Sync observations with block,
   transaction, log, source-availability, and raw identities.
3. `dex_pool_daily`: one oriented base/stable-quote row per pool/day containing OHLC,
   stable-quote volume, reserves, USD liquidity, swap count, last-swap time, and
   availability time.
4. `dex_universe_daily`: the complete per-day pool state and eligibility reason, not
   only eligible members.

Token address plus chain is identity. Pool address plus chain is venue identity. Price
orientation is frozen so a token-order reversal cannot invert returns silently.

### 5. Point-in-time membership, not permanent deletion

A pool enters the universe only after its PairCreated event is available. Daily
eligibility uses only lagged daily state. Thresholds and persistence windows are
versioned in the dataset configuration.

`ACTIVE`, `INACTIVE`, `UNAVAILABLE`, and `REVIVED` are point-in-time states. A pool is
never physically removed and a later revival is preserved. "Death" may be reported as
an inactive transition after the configured consecutive-day rule, but it is not an
irreversible fact and must not be backfilled from a current API snapshot.

Missing acquisition evidence is `UNAVAILABLE`, never zero volume, low liquidity, or
death.

### 6. Blocking data gates

No DEX experiment may begin until all gates pass:

1. **Source authority:** Ethereum chain identity, finalized cutoff, revision/reorg
   policy, provider limits, and raw-retention authority are recorded.
2. **Factory census:** PairCreated coverage is contiguous from deployment to cutoff;
   event ordinals/counts reconcile; duplicate and conflicting identities are rejected.
3. **Event completeness:** Swap and Sync block ranges are contiguous for every direct
   USDC/USDT pair, with no silent truncation or unresolved provider disagreement.
4. **Canonical reconstruction:** token decimals, orientation, OHLC invariants, reserves,
   liquidity, volume, and raw lineage reconcile deterministically.
5. **Survivorship validation:** known inactive and revived pools are reconstructed at
   historical dates, and no current-liquidity filter changes the census.
6. **As-of validation:** delayed source availability and lagged membership prevent
   future events or same-day closes from controlling a decision.
7. **Coverage report:** complete counts, spans, missing ranges, active/inactive states,
   and usable cross-section are reported. No arbitrary minimum pool count can replace
   completeness.

Any failed gate blocks publication of a research-authoritative PASS dataset. Partial
data may be retained as acquisition evidence but cannot feed a factor.

### 7. Holdout reservation before backfill

The calendar year 2025 (`2025-01-01T00:00:00Z` through
`2025-12-31T23:59:59Z`) is reserved now as the first DEX experiment holdout. This
reservation occurs before full Swap/Sync backfill or factor analysis.

- Development and data-quality work may use pre-2025 observations.
- Holdout processing may verify hashes, schema, coverage, and structural invariants,
  but must not expose factor values, return summaries, rankings, or portfolio outcomes.
- Any pool/outcome previously used in a DEX factor analysis must be listed in a
  contamination ledger before pre-registration.
- The holdout is opened exactly once, only after the data substrate is accepted and one
  factor/configuration is signed.

This provides a historical but repository-untouched holdout, so a valid result does not
require waiting for another prospective year.

### 8. Experiment remains downstream

DEX-003 is data work only. It may not implement, choose, tune, or run a factor. After
the substrate passes, a separate pre-registered experiment may add the smallest adapter
from `dex_pool_daily` and `dex_universe_daily` into the existing as-of factor contract.

The first experiment tests one transparent factor once. Until DEX-specific gas, pool
fees, routing, and price impact are evidenced, its claim is limited to predictive or
gross-return research. It cannot claim executable net return, promotion, PAPER, or LIVE.

## Consequences

- The prior current-pool/web-API design in DEX-003 is superseded for historical
  research authority.
- The current screened GeckoTerminal snapshot remains useful for operational
  cross-checks but cannot authorize an experiment.
- Broadness is achieved by complete coverage of a bounded venue, then expanded one
  complete factory/domain at a time. It is not achieved by combining incomplete lists
  from many providers.
- Data acquisition and validation precede factor work. A failed source or completeness
  gate stops the program before another invalid experiment is produced.
- No LIVE work is authorized.
