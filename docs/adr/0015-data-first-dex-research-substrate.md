# ADR-0015: Data-First DEX Research Substrate

**Status:** ACCEPTED
**Date:** 2026-07-28
**Amended:** 2026-07-30 (high-throughput event acquisition); 2026-08-05
(provider-capacity selection)
**Governing ticket:** DEX-003
**Authority:** Lead Quantitative Finance Researcher/Engineer, Max architecture pass;
Sol 5.6 provider-capacity amendment

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

### 9. High-throughput event acquisition amendment

The original scalar execution plan produces 29,709,060 `(pool, topic, 5,000-block)`
units and requires at least 118,836,240 RPC calls before event-block headers. At the
measured 1,811 receipts per hour it would take about 1.9 years. Adding workers cannot
remove that request count and would make the existing SQLite/raw-writer boundaries unsafe.

This amendment changes acquisition mechanics only. The complete domain, dual-provider
authority, raw retention, temporal semantics, holdout, and blocking gates above remain
unchanged.

#### 9.1 Versioned block-major plan

The authoritative event plan is identified by a canonical hash over:

- the accepted `dex_pool_registry` dataset ID;
- Ethereum chain and canonical factory identities;
- deployment anchor 10,000,835 and cutoff block 25,600,000;
- 5,000-block root windows;
- the ordered Swap and Sync topics;
- initial address-cohort size and deterministic split-policy version;
- credential-free provider organization identities;
- log-identity and receipt schema versions.

For each root window, include every registry pool born on or before the window end. Sort
addresses deterministically and partition them into initial cohorts. The initial cohort
is selected only by the authenticated live provider-capacity procedure below. No cohort
size is frozen in advance.

Each provider receives the same filter with an address array and a topic-position OR for
Swap and Sync. A pool born inside a root is covered only from its creation block, even
though the shared filter starts at the root boundary. Topic-combined acquisition does not
combine semantic rows: replay still partitions by pool address and event topic.

At 64 addresses this plan has 233,694 root filters before adaptive splits, a 127x
reduction from the scalar filter count.

#### 9.2 Deterministic adaptive leaves

Every query node has a deterministic ID derived from the plan ID and its block interval,
sorted address set, and topic set. A parent contributes no coverage after it is split.
Terminal agreed children must form a disjoint, exact partition of the parent domain.

- HTTP 429 and quota pressure trigger bounded backoff and lower concurrency, not splitting.
- Explicit block-range limits split the block interval.
- Oversized bodies/results, provider result-limit errors, or repeated size-related timeouts
  split the address set first; singleton-address nodes then split the block interval.
- A successful response at or above a configured conservative log/body cap is split before
  it may become authority.
- Provider disagreement is retained, retried only under the versioned policy, and then
  split to localize the disagreement. One address at one block remains fail-closed.

All started provider responses, including failed and superseded parent attempts, are
retained before cancellation or retry.

#### 9.3 Dual-provider identity v2

Paired provider calls run concurrently but are authoritative only after both raw responses
are durably retained and reconciled. Provider independence is by organization, not URL,
label, endpoint, or API key. Multiple keys from one vendor remain one authority.

The v2 order-independent log identity includes every field that can affect a published
row: address, block number/hash, transaction hash/index, log index, all topics, data, and
removed status. This corrects the v1 digest omission of `transactionIndex`. Malformed,
removed, duplicate, out-of-range, out-of-cohort, or unsupported-topic logs fail closed.

#### 9.4 Durable scheduler and persistence ownership

Query state is database-authoritative: `PENDING -> IN_FLIGHT -> AGREED` or `SPLIT`, with
expiring leases for crash recovery. JSON cursors and pool offsets are progress displays,
never completeness authority. Duplicate workers must converge on one terminal node and
verify the winner rather than race terminal inserts.

Network workers perform bounded HTTP only and return bounded response envelopes or spool
descriptors. One persistence coordinator owns raw-object/catalog registration, receipt
mutations, failure/disagreement records, and deterministic commit ordering. SQLite
connections and `RawObjectWriter` instances are not shared across worker threads.

Provider-global token buckets and in-flight limits cover every RPC method. Primary and
secondary calls for one node may overlap, and multiple nodes may be in flight, but all
started responses are drained and retained before stop-on-error completes. Queue depth,
response bytes, memory, retries, 429s, and writer latency are bounded and reported.

#### 9.5 Global canonical headers

Acquire each required event or boundary block header once per provider authority, then
persist one dual-agreed canonical-header receipt. Both providers must agree on block hash
and timestamp. Event leaves reference these shared receipts instead of reacquiring the
same block header for each pool/topic query. The in-memory header cache is bounded; the
receipt/raw store is the durable cache.

#### 9.6 Exact per-pool coverage

For every selected pool and each of Swap and Sync, the expected domain is the inclusive
block interval from pool creation through cutoff. Terminal `AGREED` v2 leaves must form an
exact, non-overlapping union of that domain after birth clamping. The coverage product
records expected/covered block counts, first/last block, leaf/event counts, gaps,
overlaps, unresolved failures/disagreements, and a deterministic hash of supporting
receipts.

An agreed empty leaf proves no matching event. A missing leaf remains `UNAVAILABLE`.
Existing scalar v1 receipts and the accepted pilot remain audit/cross-check evidence but
receive no v2 coverage credit; v2 reacquires their domains to avoid mixed digest and
receipt semantics.

#### 9.7 Separate provider phases

Event logs use independent Infura and BlockPI authority. Historical token metadata uses
independent Infura and Alchemy archive authority. The orchestrator exposes explicit event
and metadata phases rather than forcing one provider pair to support both workloads.
Token metadata calls authenticate Ethereum chain identity before durable receipt credit.

#### 9.8 Provider-capacity selection

The live matrix tests nested address prefixes of 1, 8, 32, 64, and 128 for each frozen
sparse, medium, and hot scenario and each Swap/Sync topic. A cohort size is universally
viable only when every required scalar reference succeeds, the two independent providers
agree on the scalar union, both providers complete the corresponding batched query, and
each successful batch equals that agreed scalar union.

The selected initial cohort is the largest universally viable nested prefix. An
authenticated provider limit, body-size limit, or timeout caused by capacity pressure at
larger prefixes may establish a capacity boundary and does not by itself invalidate a
smaller universally viable prefix. Quota exhaustion, authentication or credential failure,
malformed evidence, provider disagreement, successful-response digest mismatch, or
nonmonotonic viability is not capacity evidence and blocks selection. If no tested prefix
is universally viable, the matrix does not select a cohort.

The terminal report records every scalar and batch decision plus the deterministic
capacity-selection result. Generic authentication and standalone replay must recompute
that result from retained raw evidence and reject any mismatch. A COMPLETE non-PASS run
remains authenticatable evidence; authentication never converts it to PASS.

Only one live matrix may own a canonical output root at a time. The harness must acquire
an OS-backed exclusive root lock before creating or mutating run state and hold it through
terminal sealing. Process-local or pointer-file checks are not sufficient.

#### 9.9 Performance and validity gates

Before a full v2 run:

1. Batched offline replay must equal the union of scalar reference rows, including empty
   results and pools born inside a root window.
2. Identity-v2 tests must reject a secondary-only difference in every published log field.
3. The live nested-prefix matrix over sparse, medium, and hot pre-2025 ranges must select
   capacity only under section 9.8 and must authenticate the same selection on replay.
4. Forced address and block splitting must conserve the exact parent domain and result
   union.
5. Shared headers must remain fully replayable while eliminating duplicate acquisition.
6. Crash tests at every persistence boundary must resume without lost evidence,
   duplicate coverage, or unauthenticated completion.
7. A 6-24 hour endurance pilot must achieve at least 20x the scalar baseline under the
   same provider quotas with bounded memory, queues, retries, and SQLite latency.
8. Final publication still requires zero coverage gaps/overlaps and zero unresolved
   provider disagreement for every pool/topic domain.
9. The endurance evidence must project full event-log plus shared-header acquisition to a
   target of seven days and a hard maximum of fourteen days, including observed adaptive
   split/retry amplification. Projected retained evidence must fit available storage with at
   least 2x free-disk headroom. A projection above either hard bound stops full acquisition
   for redesign even if the 20x relative-throughput floor passes.

#### 9.10 Staged full-plan production readiness

This section supersedes the separate endurance-pilot requirements in section 9.9 items 7
and 9. The pilot-plan/schema approach is retired. It duplicated the accepted durable
scheduler without improving provider, header, or storage capacity and could not establish
a reachable seven-day path under accepted execution bounds.

Readiness and eventual execution use the one complete production plan selected by the
authenticated matrix: cohort size 8, all 7,659 accepted registry pools, all root windows,
and both ordered topics. A subset must never share the production plan identity. The
production root authority is additionally pinned by:

- plan ID `plan_2b96356463410b9d0a3f4f7313a06260360853207ed1bf1e42eec9eb4d756584`;
- 1,858,348 root domains;
- 148,506,716,734 birth-clamped pool-topic-blocks; and
- SHA-256 `081a12f780d065a7596ba073ba80819d173e8d74b3b16235672da673942ea907`
  over the lexicographically ordered root `domain_id` values, each encoded as lowercase
  ASCII followed by one LF byte.

Plan construction and initialization must stream in bounded memory. An additive root-
manifest record binds the accepted registry parquet identity, root count, root digest, and
pool-topic-block total. Initialization may commit authenticated batches and resume
idempotently, but no RPC may begin until every expected root is present, no extra root
exists, the manifest is `READY`, and the full anchors above recompute.

Production claims use deterministic `domain_id` order, not a pilot rank or a caller-
selected schedule. This hash order samples the complete time/cohort lattice during staged
execution while preserving eventual exhaustive coverage. The immutable execution policy
binds the claim-order version. A covering claim index is mandatory. Claims exclude both
max-attempt terminal nodes and domains with an authenticated reconciled-log candidate;
there is no minimum-rank barrier.

Event-log agreement and header finalization are separate durable phases:

1. A node's two log responses are retained, authenticated, and reconciled under log
   identity v2. Their immutable candidate records and normalized required-block rows grant
   no coverage and atomically return the node to `PENDING` with unchanged attempt while
   releasing its lease; the candidate exclusion prevents refetching the logs. A required
   block carries the expected hash when supplied by a log; a boundary-only block has no
   expected hash until the two providers establish one.
2. Missing distinct blocks are acquired globally through bounded dual-provider JSON-RPC
   header batches. Every response is retained; response IDs, block numbers, hashes, and
   timestamps must reconcile exactly. One canonical header receipt may reference a shared
   batch acquisition, and each block is credited once globally.
3. Candidate finalization replays both log bodies and all canonical headers, then atomically
   writes the leaf/dependencies and changes the node to `AGREED`. Header disagreement,
   malformed/missing batch members, raw mismatch, or exhausted attempts remain terminal
   blockers. Candidates alone contribute zero pool-topic-blocks.

This removes sequential per-leaf header acquisition from the event-node critical path and
deduplicates headers across the full plan. Header batch size and provider/node concurrency
are execution-policy inputs selected only by a later authenticated production-readiness
preflight; current engine defaults or untested higher values are not accepted capacity
evidence.

Every network response byte must pass a bounded rolling endpoint/credential scanner before
any spool/raw write, including error and over-cap drains. The engine also requires bounded
rolling replenishment, provider-attempt and actual in-flight high-water metrics, candidate/
header backlog metrics, total retained-byte admission, and clean stop/drain behavior. All
state and raw evidence must authenticate before resume.

After source/integration acceptance and a separately authorized live readiness preflight,
the real full production plan may run in stages. Stages are checkpoints over reusable
production evidence, never sampled pilot coverage. The first six active hours must include
all provider, header, persistence, retry, split, and backlog cost and meet all of:

- at least 181,100,000 pool-topic-blocks/hour (the retained 20x diagnostic floor);
- projected full completion at or below seven days using integer arithmetic and a
  conservative authenticated rate over the hash-ordered work;
- projected remaining evidence fitting current free storage with at least 2x headroom; and
- no credential/authentication failure, unresolved disagreement, terminal blocker,
  persistence/internal failure, unknown authority, gap, overlap, or resource-bound breach.

The exact seven-day and fourteen-day mean thresholds are respectively 883,968,552 and
441,984,276 pool-topic-blocks/hour. A six-hour projection in `(7 days, 14 days]` pauses for
review and is not PASS; a projection above 14 days stops for redesign. Checkpoints repeat
at 24 hours and every 24 hours thereafter. Seven days remains the target. Fourteen days is
an unconditional stop-new-work deadline, followed by drain and authenticated non-PASS
sealing if full coverage is not complete. Final PASS still requires every section 9.6
coverage product with zero gaps, overlaps, or unresolved blockers.

No source-only, offline, readiness-preflight, or staged-start decision grants coverage by
itself or authorizes publication. A production controller, CLI, live preflight, staged RPC
start, continuation after any pause, and final publication each require explicit reviewer
authorization.

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
