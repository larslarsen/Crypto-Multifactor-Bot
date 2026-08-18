# ADR 0016 — CEX-First Full Derivatives Research Spine

- **Status:** Accepted
- **Date:** 2026-08-17
- **Supersedes in part:** ADR-0014 work ordering after DATA-011; further execution of
  ADR-0015 / DEX-003
- **Evidence:** `research/sprint_004/54_CEX_SPINE_GAP_AUDIT.md`

## Context

The repository does not yet contain a functional, microstructure-aware research data
stack. The accepted DATA-011 output is a 23-instrument Binance spot daily-bar panel,
not a venue-complete derivatives panel. The accepted Bybit work is a source normalizer
tested against two isolated public trade archives, not a production trade history or an
aligned market-microstructure product. No production dataset aligns order-book state,
trades, open interest, funding, liquidations, basis, contract identity, and costs.

Five retained BitMEX funding parquet artifacts contain 307,738 rows in total. Direct
inspection found zero nonzero `funding_rate` values and an empty `funding_interval` in
every row. All five are nevertheless cataloged `PASS`; the latest narrow and full
products resolve to invalid artifacts. The normalizer explains the false success: a
missing rate becomes `0.0`, missing/invalid daily rate is derived silently, empty interval
is accepted, and the publisher unconditionally declares `PASS`.

DATA-009, which produced the 45-symbol full artifact, remained `AWAITING_REVIEW`; it is
rejected and superseded by this decision so it cannot coexist as a second active ticket.

The Sprint-003 source audit proved that selected real archives can be parsed and supplied
storage estimates. It did not acquire or publish the full microstructure stack. Later
experiment language about realistic mechanics did not establish that those data were
consumed. Requirements, audit completion, dataset completion, research-harness
consumption, and trading readiness were allowed to look equivalent when they were not.

DEX-003 has produced valuable retained evidence and an accepted pool registry, but its
remaining acquisition is unfinished and has consumed disproportionate engineering and
review effort. Continuing it does not produce the CEX execution substrate needed by the
existing models or by a later Harmonic Trader integration.

## Decision

### 1. Strategic order

CEX-001 is the sole active engineering ticket. DATA-009 is rejected/superseded and
DEX-003 is strategically terminated as
`SUPERSEDED`, not accepted. Its code, raw evidence, databases, reports, and published
datasets remain preserved and truthfully labeled. No further DEX source correction,
integration, migration, RPC acquisition, publication, or model work is authorized unless
a future reviewer decision creates a new ticket.

No harmonic-model development begins under CEX-001. Existing model execution resumes only
after the data release and consumer harness pass their own gates.

### 2. Canonical venue and domain

The canonical research domain is **Binance USD-M linear perpetual contracts** plus the
same-venue spot/index references required for basis. This is one coherent contract family;
COIN-M, BitMEX, Bybit, OKX, and DEX data are not silent substitutes.

The acquisition universe is every USD-M perpetual contract present during the declared
source coverage, including subsequently delisted or renamed instruments. It is derived
from bitemporal contract/reference evidence. A fixed N, current listing list, current
liquidity rank, hand-picked symbol map, or current API response must never bound historical
acquisition. Point-in-time liquidity screens may later determine model eligibility, but
they do not erase data or membership.

### 3. Required immutable products

CEX-001 must publish separate immutable, non-empty products joined by canonical
instrument and contract-version identity:

1. contract/reference versions and listing/delisting events;
2. raw trades and causally derived trade-flow aggregates;
3. one-minute or finer perpetual market bars, reconciled to an independent source bar;
4. top-of-book plus fixed-depth snapshots sufficient to measure spread, depth, imbalance,
   and an explicit impact proxy at one-minute or finer frequency;
5. native and converted open-interest snapshots;
6. realized funding events, with indicative funding kept separate;
7. exchange liquidation events with proved side semantics;
8. mark, index, premium, and same-venue spot references required for basis; and
9. effective-dated fee schedules and declared execution-cost inputs.

Every row or typed gap record carries venue-native symbol, canonical instrument,
contract version, event time, source availability time where the source supplies it,
retrieval time, raw acquisition/object identity, and quality state. A missing feed is
`UNAVAILABLE` or a typed gap, never a numeric zero.

### 4. Source strategy

Official Binance archives and APIs are primary authority where they provide complete
products and checksums. They are insufficient by themselves for a defensible full
historical microstructure bundle. A licensed historical capture vendor may supply L2/BBO,
liquidations, OI, and other products only after real sample qualification proves schema,
coverage, incident metadata, contract breadth, availability clocks, licensing, and a
reproducible acquisition path.

The source qualification is not permission for a toy universe. It evaluates the full
historical contract family and produces an explicit procurement and storage decision.
No paid purchase is implied by this ADR; the owner must authorize the quoted external
cost. If no source can meet the required products, coverage, and budget, CEX-001 reports a
blocking fact and stops. It must not substitute synthetic rows, zero-fill missing data, or
quietly reduce the universe.

Where official and licensed sources overlap, trades, funding, marks, and coverage are
reconciled. Raw/downloaded objects, checksums, request/response receipts, vendor incident
records, and revisions remain immutable. Resumption must produce byte- and row-equivalent
outputs without duplicate economic rows.

### 5. Temporal and dimensional contract

The clock is:

`source event -> source_available_at <= decision_time < executable entry < exit`.

Late, revised, backfilled, or vendor-arrival-only observations retain their actual
availability semantics. Unknown source publication time is represented as unknown and
cannot be invented from event time.

Contract quantity, base quantity, quote/settlement value, USD notional, multiplier,
linear/inverse style, settlement asset, mark/index conversion price, and conversion time
are distinct fields. Funding sign and long/short cashflow semantics, OI conversion, and
liquidation side are independently tested against retained real source examples.

### 6. Release and consumer boundary

Acceptance requires a versioned bundle descriptor pinning every dataset/manifest ID,
schema, mapping, coverage interval, typed gap product, source/config/code identity, and
cross-product intersection count. The release must be consumable through a clean,
versioned package build and bulk/as-of API; it may not depend on a dirty checkout or an
uncheckpointed SQLite WAL.

The first consumer harness must fail closed on a missing, empty, stale, incompatible, or
unreconciled component. It must enforce strictly later executable entry, explicit funding
and cost accounting, dimensional position semantics, deterministic resume, and run
fingerprints. It may prove mechanics on a declared development interval but may not emit
harmonic features, factor payoff screens, holdout outcomes, PAPER promotion, or LIVE
claims under CEX-001.

### 7. Evidence labels

The repository must distinguish these states:

- source feasibility;
- source authority accepted;
- raw coverage complete;
- normalized product accepted;
- aligned bundle accepted;
- consumer harness accepted;
- experiment executed; and
- PAPER/LIVE eligible.

No earlier state implies a later one. Reports that merely count rows cannot declare
`PASS` when economic fields are missing, constant because of fallback behavior, or outside
the required cross-product intersection.

## Consequences

- The 23-name daily spot panel remains valid only for its accepted limited purpose; it is
  not called the CEX spine or microstructure-aware data.
- All five invalid BitMEX funding products are quarantined in place and excluded from
  latest-resolution and research consumption before new data publication.
- CEX breadth is historical venue membership, not a nominal U20/U50/U100 shortcut.
- Historical market microstructure may require a commercial source and material storage.
  That cost is surfaced before purchase, with no silent scope reduction.
- Existing models are run only after the full CEX release/harness is accepted. Harmonic
  Trader integration is a later consumer, not part of this data build.
