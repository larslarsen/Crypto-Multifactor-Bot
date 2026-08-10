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

#### 9.11 Production controller, readiness evidence, and stage authority

Section 9.10 defines the production data path but intentionally does not grant a process the
authority to run it. This section freezes the missing control plane. It is additive: the
accepted scheduler remains the only query scheduler, the accepted log-candidate/header/leaf
path remains the only coverage path, and a readiness run remains non-credit evidence in a
separate root. No controller may install a second plan, sampled production plan, rank barrier,
or alternate coverage ledger.

##### 9.11.1 Authority and isolation boundaries

Exactly one production controller may own the canonical production database/raw/spool root.
It acquires an OS-backed exclusive lock before opening mutable production state and a matching
durable controller lease before any engine network entry point. It holds both through
stop-new-work, drain, engine/client close, checkpoint authentication, and terminal sealing.
Losing either authority is an immediate stop. Multi-process scheduler support remains a
recovery property, not permission for concurrent DEX-003 production controllers.

Every production network entry point, including chain authentication, log fetch, header batch,
retry, and candidate finalization, must authenticate an active stage capability against the
durable plan, runtime policy, reviewer permit, controller lease, and stage state. Calling the
accepted engine directly with the production plan and only a READY root manifest must fail
closed. Generic/non-production engine behavior is unchanged.

Readiness uses a dedicated root, receipt database, raw store, spool, lock, manifests, and
terminal. It must refuse `dex003_full.db`, the production raw/spool/controller roots, accepted
registry/catalog paths, matrix evidence trees, symlinks, and any related/overlapping path. It
does not insert a production plan/query node, does not call a production claim, and cannot
write a leaf, dependency, coverage product, or production credit. It exercises the same public
stream scanner, network attempt, raw persistence, JSON-RPC authentication, split, and header-
batch primitives as production; a private fork of those semantics is prohibited.

##### 9.11.2 Frozen readiness specification

The readiness workload is the 128 lexicographically lowest `domain_id` values from the exact
1,858,348-root production authority. Selection streams the complete root iterator, keeps only
the lowest 128 identities, then sorts those 128 identities ascending. The selected identity set
has SHA-256 `7f009be09d1268008d69940078fea3e62264314d39754ed8f399537e283b90ea`
over each lowercase ASCII `domain_id` followed by LF and represents exactly 10,240,000 birth-
clamped pool-topic-blocks. All 128 are full eight-address roots; their block windows span
11,665,835 through 25,570,834. This sample is a deterministic capacity probe, not a statistical
completeness claim and not production credit.

The canonical compact sorted-key JSON readiness payload is:

```json
{"attempts_per_logical_call":3,"chain":"ethereum","cutoff_block":25600000,"event_provider_orgs":["infura","blockpi"],"matrix_live_evidence_hash":"e42e987dade698af6af4fb47598abe88eb78116ac6fc004ff6fc4d0a84b4a114","matrix_live_report_hash":"2062d1f8717672de645f07bd761354bea31cdca9dbe20908cfe3941fb00189ef","matrix_live_run_id":"run_f2fd323fcd69403a923f6329b9f0c320","matrix_replay_evidence_hash":"f7b536de7823a298688e935efae82f85971957c440c7ccdea96881b0b72b88a2","matrix_replay_report_hash":"6c27a8df5211991487d2d0d61dbac548a94f2f4c41a17393ee2846a5ec165786","matrix_replay_run_id":"run_bd066d2e228d46728a97fdb61138e365","max_distinct_header_blocks_per_rung":4096,"max_response_bytes":8000000,"max_retained_bytes":8589934592,"max_wall_seconds":7200,"plan_id":"plan_2b96356463410b9d0a3f4f7313a06260360853207ed1bf1e42eec9eb4d756584","production_pool_topic_blocks":148506716734,"production_root_count":1858348,"production_root_domain_set_sha256":"081a12f780d065a7596ba073ba80819d173e8d74b3b16235672da673942ea907","readiness_schema_version":"1","registry_dataset_id":"ds_42ce2515e226258557a06a374498547393bbc984db791c56fa19d81d7ef16d15","registry_parquet_bytes":1606417,"registry_parquet_sha256":"8e41a9fb1e1b05f126345ca0a7a9eb04792cd0e92d45406a9b5c031105d83256","root_sample_count":128,"root_sample_domain_set_sha256":"7f009be09d1268008d69940078fea3e62264314d39754ed8f399537e283b90ea","root_sample_order":"lowest_domain_id_v1","root_sample_pool_topic_blocks":10240000,"rungs":[{"header_batch_size":8,"max_in_flight_per_provider":1,"max_nodes_in_flight":1,"requests_per_second_milli":500},{"header_batch_size":8,"max_in_flight_per_provider":1,"max_nodes_in_flight":1,"requests_per_second_milli":1000},{"header_batch_size":16,"max_in_flight_per_provider":2,"max_nodes_in_flight":2,"requests_per_second_milli":2000},{"header_batch_size":32,"max_in_flight_per_provider":4,"max_nodes_in_flight":4,"requests_per_second_milli":4000},{"header_batch_size":32,"max_in_flight_per_provider":4,"max_nodes_in_flight":4,"requests_per_second_milli":8000},{"header_batch_size":64,"max_in_flight_per_provider":8,"max_nodes_in_flight":8,"requests_per_second_milli":8000}],"split_policy_version":"1","topics":["0xd78ad95fa46c994b6551d0da85fc275fe613ce37657fb8d5e3d130840159d822","0x1c411e9a96e071241c2f21f7726b17ae89e3cab4c78be50e062b03a9fffbbad1"]}
```

Its identity is
`rdy_abadab41f5f4221a0f2e5c36e11b5bbe3893393dfab85e614be65ff2f26975bb`.
Integers are authoritative; `requests_per_second_milli / 1000` is only a runtime
conversion.

Before a live readiness attempt creates state, it authenticates the accepted registry and the
accepted clean matrix live/replay terminals, including cohort 8, provider organizations, run
IDs, evidence hashes, and report hashes recorded in the active DEX-003 governance record. It
also records and scans the exact accepted source, migration, and CLI hashes. Endpoints and
credentials remain runtime-only.

Rungs execute in the listed order. Each rung independently acquires both providers' chain ID,
then runs all 128 production-shaped combined-topic roots through the shared bounded transport,
raw persistence, exact split policy, global distinct-header batching, and zero-network replay.
Every attempt is retained before retry/stop. Adaptive descendants inherit only their source
sample root and rung; they never become production nodes or credit. A rung is capacity-eligible
only if all 10,240,000 PTB reconcile and replay, every logical call succeeds on its first
attempt, and it has zero 429, credential/endpoint detection, authorization failure, truncation,
transport/RPC/malformed response, provider disagreement, unsplittable terminal, persistence/
internal error, unknown authority, leaked worker, spool residue, or resource-bound breach.
A capacity failure stops higher rungs. A credential, chain, raw-authentication, provider-
disagreement, persistence, or unknown-authority defect fails the entire readiness run.

For an eligible rung, `active_ns` starts immediately before its first chain request and ends
only after all response work, raw fsync, replay, metrics, and clean close complete. The exact
reachability test applies a 20% haircut without floating point:

```
4 * 10_240_000 * 604_800_000_000_000
    >= 5 * active_ns * 148_506_716_734
```

The readiness report partitions the ordered sample into four consecutive groups of 32 and
records exact variable raw/receipt/database bytes per group. Log/split bytes belong to their
source root; a shared header belongs to the lexicographically lowest sampled root requiring it;
chain/controller/manifest bytes are fixed overhead. Let `bptb_max` be the largest group
variable-byte/PTB rational and `fixed_bytes` the reconciled fixed overhead. With actual
production initialization not yet performed, the provisional storage inequality is exactly
`free_bytes >= 2 * (ceil(148_506_716_734 * bptb_max) + fixed_bytes +
current_immutable_production_tree_bytes)`. Production arming repeats the gate using the actual
initialized database/tree and remaining PTB.

The selected policy is the highest contiguous capacity-eligible rung satisfying both exact
reachability and provisional storage gates. No eligible rung means COMPLETE/non-PASS and no
production initialization. A safety defect means FAILED. The terminal inventories/hashes every
allowed readiness file, authenticates every receipt/raw pairing and split/header result, rejects
extras/path escapes/non-regular objects/WAL/spool residue, reproduces rung decisions and policy
selection from disk with zero network, and scans all artifacts for credentials. Neither outcome
authorizes production initialization or RPC.

##### 9.11.3 Runtime policy and production initialization

After separate reviewer acceptance of a COMPLETE/PASS readiness terminal, its selected rung is
sealed into one immutable production runtime policy. Its content-addressed identity binds the
readiness identity/run/evidence/report hashes, selected rung, full source/migration hashes,
accepted matrix and registry identities, engine bounds, retry/split versions, scanner version,
and the exact database/raw/spool/controller roots. Runtime options may only lower non-identity
operational deadlines; they may not raise or substitute RPS, in-flight, node, header-batch,
response, queue, spool, attempt, or retained-byte bounds.

Production initialization is a separately reviewed offline operation after policy acceptance.
It authenticates the registry again, applies the selected policy, streams the complete root set
to the existing additive foundation, and seals the root manifest READY only after all section
9.10 anchors recompute. It then replays every structural row, confirms no leaf/candidate/header/
credit exists, checkpoints SQLite, records the actual database/tree bytes and free space, and
repeats the 2x remaining-storage gate. It performs no RPC. Failure leaves an authenticatable
non-READY or non-armed state and grants no stage authority.

##### 9.11.4 Additive production-control persistence

Forward migration 0021 is additive only and may not rebuild, weaken, delete, or rewrite any
0017-0020 table or row. It adds these normalized authorities with inline foreign keys and exact
CHECK domains:

1. `uniswap_v2_pair_event_v2_runtime_policy`: one immutable row per production plan, with the
   content-addressed policy payload and accepted readiness/report/source hashes.
2. `uniswap_v2_pair_event_v2_stage_permit`: one immutable content-addressed reviewer permit per
   stage. It binds plan/policy, ordinal, allowed transition, active/wall bounds, not-before/
   not-after UTC instants, the governing-record commit, and prior terminal (if any).
3. `uniswap_v2_pair_event_v2_production_stage`: one row per stage with the permit, baseline
   credited PTB, and state domain `PREPARED`, `AUTHORIZED`, `RUNNING`, `DRAINING`,
   `PAUSED_REVIEW`, `BLOCKED`, or `COMPLETE`. Only the frozen transition graph may update its
   state; identities and baselines are immutable.
4. `uniswap_v2_pair_event_v2_controller_lease`: at most one row per plan, binding stage,
   controller instance, capability-token SHA-256, acquired/renewed/expiry times, and lease
   generation. The plaintext capability is runtime-only.
5. `uniswap_v2_pair_event_v2_controller_event`: an append-only per-stage sequence of canonical
   `START`, `CHECKPOINT`, `STOP_REQUEST`, `DRAINED`, `CRASH`, `RESUME`, and `END` events. Each
   row binds the previous event hash, boot/process identity, wall time, monotonic nanoseconds,
   payload hash, and its own content hash.
6. `uniswap_v2_pair_event_v2_stage_attempt`: append-only stage attribution for every chain/log/
   header attempt, including no-response and scanner-rejected attempts. Provider organization,
   role, logical-call ID, attempt, domain/block identity, start/end/latency, status, byte counts,
   and canonical outcome are mandatory. Acquisition/raw IDs are both NULL or both non-NULL; when
   present they carry the exact composite `(acquisition_id, raw_object_id)` FK. A credential hit
   therefore records only the redacted outcome and no raw pair.
7. `uniswap_v2_pair_event_v2_leaf_credit`: exactly one immutable row per production leaf,
   binding plan/domain/leaf/stage and exact integer birth-clamped PTB. It has same-plan FKs to
   the leaf and stage. Credit insertion is atomic with candidate finalization; later
   authentication recomputes PTB from the pinned registry and rejects parent/child double credit.
8. `uniswap_v2_pair_event_v2_stage_checkpoint`: immutable, hash-chained checkpoint rows with
   cumulative authenticated PTB/leaf/raw counts, node/terminal/backlog counts, clock totals,
   exact metrics, logical evidence roots, byte/free-space facts, and rational projection inputs.
9. `uniswap_v2_pair_event_v2_stage_terminal`: exactly one immutable terminal per stage, binding
   the final checkpoint, event-chain root, manifest/report hashes, outcome, and next-authority
   requirement.

All immutable tables reject UPDATE/DELETE with triggers. The mutable stage/lease operations are
transactional coordinator APIs, never caller SQL. Covering indexes serve active-stage lookup,
event/checkpoint order, stage/raw inventory, leaf-credit aggregation, and terminal lookup. The
migration must pass a populated 0020 upgrade preserving all prior counts/identities/FKs, fresh
apply, forced atomic rollback, exact index-plan, mutation-trigger, cross-plan/stage mismatch,
and composite raw-pair rejection tests.

##### 9.11.5 Stage state, clocks, and permits

A permit is canonical JSON whose `permit_<sha256>` identity must appear verbatim in an active
reviewer authorization before `run-stage` can transition `PREPARED -> AUTHORIZED`. A permit is
single-use, names one stage ordinal, cannot outlive its UTC `not_after`, and cannot authorize
publication. Stage 1 permits new work only until the first credited active monotonic checkpoint
at or after six hours; only bounded drain/authentication may follow. Later permits end no later
than the next 24-hour boundary from the immutable first production start, and every
continuation after a pause requires a new permit. The first production start fixes a global
fourteen-day wall deadline that no permit can extend.

Each process segment appends START before work and durable CHECKPOINT events at least every 60
seconds, at every controller transition, and immediately before/after drain. A normal END credits
monotonic time only through its last checkpoint. An unmatched/crashed segment receives credit
only through its last durable checkpoint; the next process must fully authenticate prior state,
append CRASH and RESUME, and may not resume RPC without a new reviewer permit. Wall time is the
UTC difference from immutable first START to the decision checkpoint, so downtime cannot improve
throughput. Wall regression, an impossible wall/monotonic relation, torn/noncontiguous events,
or a missed hard deadline is a blocker. No float participates in identity or gates.

At the stage limit or any stop, the controller first disables new claims/header batches, requests
engine stop, drains every started response and persistence command, resolves or expires owned
leases according to accepted semantics, closes all engine threads/clients, checkpoints SQLite,
and only then authenticates and seals. A signal is a controlled PAUSED_REVIEW only if that entire
sequence succeeds; otherwise it is BLOCKED. A crash never earns a passing performance checkpoint,
although its already authenticated leaves remain reusable production evidence.

##### 9.11.6 Checkpoints, projection, and storage

The only throughput numerator is the sum of authenticated `leaf_credit.pool_topic_blocks`.
Claims, attempts, candidates, headers, logs, parent domains, in-flight nodes, and asserted metrics
are never credit. At each decision checkpoint:

```
credited_ptb       = authenticated cumulative production leaf credit
remaining_ptb      = 148_506_716_734 - credited_ptb
elapsed_wall_ns    = decision_wall_utc - immutable_first_start_wall_utc
projected_total_ns = elapsed_wall_ns
                   + ceil(remaining_ptb * elapsed_wall_ns / credited_ptb)
```

`credited_ptb = 0`, negative/overflowing values, duplicated coverage, a gap/overlap, or credit
above the full authority is non-PASS. Stage 1 is not eligible for continuation until it has at
least 21,600,000,000,000 checkpoint-credited active nanoseconds and its exact wall-rate cross-products prove
both at least 181,100,000 PTB/hour and `projected_total_ns <= 604,800,000,000,000` (seven days).
Projection in `(seven days, fourteen days]` is PAUSED_REVIEW/non-PASS. Projection above
1,209,600,000,000,000 nanoseconds, or reaching that wall deadline incomplete, is BLOCKED for
redesign. These classifications do not override any safety blocker.

Every checkpoint reconciles bytes exactly once across attributed raw objects, SQLite growth,
controller/checkpoint artifacts, and fixed initialized state. The future variable-byte ratio is
the maximum authenticated byte/PTB rational among the four readiness groups and every completed
production checkpoint interval; unattributed growth is fixed/growing overhead, never discarded.
The remaining projection uses that maximum ratio plus measured fixed/growing overhead. Current
free bytes must be at least twice the projected additional bytes. A filesystem-capacity decline,
unattributed byte, overflow, or 2x failure stops new work before another response begins.

Immediate blockers are credential/endpoint detection; registry/root/policy/permit/lock/lease/hash
drift; chain/provider/raw disagreement; malformed/truncated/unknown evidence; terminal node;
unresolved gap/overlap; persistence/internal failure; response/attempt/queue/spool/retained-byte/
disk/deadline breach; or failure to drain and close. HTTP 429 or transport retry is retained and
included in the rate, but exceeding the immutable selected-policy bounds is a resource blocker.

##### 9.11.7 Sealing and zero-network authentication

Each readiness or production stage has a canonical controller directory. A pre-terminal
`MANIFEST.json` inventories every allowed regular file except the held lock and terminal itself,
rejects symlinks/hard links/path escapes/extras, and binds the stage's canonical logical row/raw
roots in production state. `TERMINAL.json` is exclusive-created after clean close and hashes the
manifest plus every identity, clock, counter, metric, byte, projection, gate, outcome, and prior-
terminal field with only its own hash fields omitted. No stage-directory write is allowed after
terminal creation.

The public authenticator opens databases immutable/read-only and performs zero network. It
recomputes permits/policies/event chains/checkpoints/terminals, registry/root anchors, exact source
hashes, every attributed acquisition/raw byte-count/hash/canonical URI, requests/provider/attempt
identity, candidate/log/header/leaf/dependency/terminal semantics, split conservation, PTB credit,
metrics, clocks, projections, storage arithmetic, credential scans, and filesystem inventories.
Unknown/orphan/unattributed authority, WAL/SHM/spool/lease residue, missing or extra objects, and
any mismatch fail closed. A COMPLETE full-coverage candidate still grants no publication; final
coverage-product construction, dataset publication, and reviewer acceptance remain separate gates.

##### 9.11.8 CLI and authorization sequence

The production CLI exposes only these roles: `readiness-plan` (offline), `readiness-run` (live,
separately authorized), `readiness-authenticate` (offline), `production-prepare` (offline,
separately authorized after readiness acceptance), `production-status` (read-only), `stage-run`
(live, exact reviewer permit and confirmations), and `stage-authenticate` (offline). Live commands
require their explicit execute flag plus exact readiness/plan/policy/permit confirmations. Caller-
supplied pools, roots, ranges, topics, providers, schedules, database identities, or policy values
are rejected. Commands, reports, exceptions, and durable metadata never contain endpoint or secret
values.

Authorization order is strict: architecture publication; source/test implementation and source
review; offline Jr integration acceptance; separate live-readiness authorization and result review;
separate offline production-prepare authorization and result review; then a separate permit for the
first six-hour stage. Each later stage, final coverage construction, publication, and downstream use
requires its own reviewer decision. Skipping a gate is an architecture violation.

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
