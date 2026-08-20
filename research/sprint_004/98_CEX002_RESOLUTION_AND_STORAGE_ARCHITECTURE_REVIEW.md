# CEX-002 Resolution and Storage Architecture Review

Date: 2026-08-20

Reviewer: Lead Quantitative Finance Researcher/Engineer

Reviewed execution evidence:

- `research/sprint_004/96_CEX002_GATE1_PLAN2_EXECUTION.md`
- `research/sprint_004/97_CEX002_GATE1_PLAN2_EXECUTION_REVIEW.md`
- `research/sprint_004/62_CEX002_GATE1_SOURCE_PROCUREMENT.json`

Architecture publication base: `e1f347fe2a8dc6ed9941ac40c9f363a56e7a3c1d`

Harmonic design evidence inspected from `/home/lars/Harmonic_Trader`:

| Document | SHA-256 |
|---|---|
| `research/CEX_DERIVATIVES_DATA_REQUIREMENTS.md` | `d1b87d1746dced01147452a3616bc57189fe5e98b7bb82f15b9cfa204653f4ce` |
| `research/autonomousgemetricdiscovery.md` | `80570783db94b7bad8a4eb62f11f3104039b0cfda29c9f74ff0c1a46eee624cd` |
| `research/GEOMETRIC_DISCOVERY_EXPERIMENT_PROTOCOL.md` | `b07db6a8b0cfa0120959fa1e8f0e576d7548332dca97b6befdc86d060024c44b` |
| `docs/upstream/PROPOSED_TICKET_CEX_DERIVATIVES_BUNDLE.md` | `9d8381fd33c79444d5dbff5a2f1e021fe69a227b238bdcbdc508bfbb72bef5cc` |

These documents are currently untracked in that separate working tree, so the content
hashes, not its Git `HEAD`, identify the reviewed design evidence.

## Decision

**AMEND ADR-0017 AND CEX-002. REJECT REVIEW 97'S STORAGE DISPOSITION. RETURN GATE 1 TO
`IN_PROGRESS`.**

Review 97 remains accepted evidence of a reproducible execution, an exact inventory under
the then-current contract, qualified Coinalyze access, stable resume identity, and unresolved
historical membership. It is not accepted evidence that Harmonic Trader requires 8.66 TB.
The Owner is not required to provide storage or purchase data.

## Finding 1: the model contract does not require ticks or historical books

The Harmonic input vector is price geometry plus terminal-leg OI change, funding state, and
long/short liquidation imbalance. The detailed data contract requires hourly-or-finer OHLCV,
OI snapshots, funding, liquidation, basis references, fees, spread/quote evidence, and a
declared cost model. It does not require individual trades, aggregate trades, or a complete
historical order book.

ADR-0017 and CEX-002 expanded that contract to source-granular trades, one-minute bars, all
freely available book/depth evidence, and a prospective stream collector. That expansion was
reviewer-authored and unsupported by the cited Harmonic design. Removing it is a correction
to the target contract, not a price-only substitute or reduced-universe experiment.

Native one-hour Binance klines contain OHLCV, trade count, total base/quote volume, and
taker-buy base/quote volume. They therefore support the required hourly price geometry,
volume, and taker imbalance without a tick-tape reconstruction.

## Finding 2: the 8.66 TB figure counts redundant representations

The accepted inventory reports:

- 6,174,436,174,147 logical trade bytes across `trades` and `aggTrades`;
- 2,448,204,498,577 logical cost bytes across `bookTicker` and `bookDepth`;
- both daily and monthly archive packaging for trades, aggregate trades, klines,
  mark/index/premium klines, and book ticker; and
- 5,123,061 unique object keys, which are not 5,123,061 unique economic intervals because
  daily objects and their monthly package can represent the same observations.

Physical-key deduplication correctly avoided counting one exact key twice across logical
products, but it did not and could not remove economic duplication across different daily
and monthly keys or across trade representations. The storage figure answers how large all
objects under the inflated contract are. It does not answer how large the Harmonic-ready
release must be.

## Corrected historical release contract

The acquisition universe remains every affirmatively identified historical Binance USD-M
crypto perpetual, including delisted contracts. Required immutable products are:

1. perpetual membership and contract identity;
2. native one-hour perpetual OHLCV bars;
3. one-hour bar-derived volume and taker flow;
4. native five-minute OI and available positioning/taker metrics;
5. realized funding events;
6. hourly indicative funding/premium observations;
7. hourly mark/index/premium basis observations;
8. observed/censored daily long/short liquidation aggregates;
9. effective fee schedules and the bounded cost-calibration sample;
10. typed per-product gaps and intersection membership; and
11. a pinned Harmonic bundle and clean Nautilus catalog-load check.

Historical `trades` and `aggTrades` are not selected acquisition families. Full historical
`bookTicker` and `bookDepth` are not selected acquisition families. The cost product uses a
frozen, outcome-blind first/midpoint/last whole-day sample from each of
`daily/bookTicker` and `daily/bookDepth` for each accepted contract. This is real
spread/depth evidence across contract lifecycles, while honestly remaining calibration
evidence rather than an exact historical fill tape.

The qualifier may continue to list any official family to discover candidate contract names.
Listing a family never promotes all of its objects into the acquisition manifest.

## Canonical cadence selection

For a family available in daily and monthly packages, a checksum-valid monthly object is the
canonical raw source for a completed month. Daily objects are selected only where no accepted
monthly object represents the date, including current tails and explicit monthly gaps. The
selected manifest must bind each object to its economic interval and reject overlaps.

An invalid monthly object remains quarantined provenance if discovered after selection. A
daily fallback may replace its economic coverage, but the invalid monthly object is not a
second consumable representation. Immutable plan history records the transition.

## Coverage semantics

The source acquisition universe is never reduced to current listings, a fixed N, or the
Coinalyze-supported subset. A missing product becomes a typed gap. The 202 affirmed Coinalyze
non-mappings exclude those contracts only from the liquidation-complete G2 intersection;
they do not block publication of real supported histories and do not become zeros.

The 63 archive-only contract names remain unresolved membership authority. They must be
classified from retained official evidence before the membership gate passes. That is a
reviewer/source investigation task, not a request that the Owner invent or purchase an
authority source.

## Corrected storage gate

The next real qualification must calculate storage from the non-overlapping selected
manifest. It reports items 1 and 2 exactly and leaves items 3 through 5 explicitly unknown.
A later bounded normalization-sizing step must resolve those fields. Gate 2 remains
unauthorized until measured free space can hold all of:

1. selected compressed raw objects and Coinalyze receipts;
2. the complete declared cost sample;
3. a conservative normalized/catalog bound based on retained real samples;
4. the largest atomic-download/normalization temporary high-water requirement; and
5. a declared operating reserve.

The report separately retains total discovered listing bytes for audit. Unselected trades,
unselected books, and overlapping cadence packages do not consume the release budget. No
gigabyte estimate is accepted until the revised real inventory runs; no terabyte purchase or
external storage is authorized.

Plan version 3 receives a new, separately ledgered ceiling of 268,435,456 additional sample
bytes. The earlier 1,015,198,547 retained bytes and its unresolved legacy budget breach remain
reported as historical evidence; they are neither erased nor charged again. Compatible
retained samples are reused. There is no separate 64 MiB object cap: an object that cannot
fit within the remaining total allowance is reported with its exact size and blocks rather
than being silently skipped or truncated.

## Bounded Grok source authorization

Sr Dev - Grok Build using Grok 4.6 High is authorized to edit only:

- `src/cryptofactors/acquisition/binance_usdm_harmonic_qualification.py`;
- `scripts/research/qualify_binance_usdm_harmonic_sources.py`;
- `tests/acquisition/test_binance_usdm_harmonic_qualification.py`; and
- `tests/acquisition/fixtures/binance_usdm_harmonic_qualification/`.

The source/test drop must:

1. replace the historical source-product matrix with the corrected products and native
   `1h` kline intervals while retaining native five-minute metrics and funding events;
2. separate discovery-only archive families from selected acquisition families;
3. construct an immutable non-overlapping acquisition manifest with monthly-preferred,
   daily-gap/tail fallback and explicit economic-interval collision rejection;
4. derive hourly taker-flow availability from the known kline schema and never require
   `trades` or `aggTrades` for that product;
5. construct the exact first/midpoint/last per-contract daily `bookTicker`/`bookDepth` cost
   sample and report its bytes separately from full archive inventory;
6. calculate exact selected raw/cost-sample bytes and largest selected compressed object;
   keep normalized, temporary-high-water, reserve, and total-sufficiency fields explicitly
   unknown in this phase rather than inventing a bound;
7. treat explicit Coinalyze non-mappings as typed product/intersection gaps, not source or
   release failure;
8. remove prospective stream acquisition from this ticket while retaining a pinned holdout
   boundary and honest retrieval/availability clocks;
9. preserve plan versions 0 through 2 and emit an immutable candidate version-3 plan plus
   prior-lock hash, new input hashes, distinct content digest, and migration assertions;
   no public relock switch or actual migration is authorized in this drop, and changed
   content must never reuse the old digest; and
10. add focused test source for every rule above while preserving the complete accumulated
    test file.

The candidate plan uses the separately ledgered 268,435,456-byte architecture-amendment
allowance above, reuses compatible retained evidence, removes the independent 64 MiB
per-object cap, and preserves the complete legacy budget record. A later reviewer decision
must inspect the exact candidate before authorizing any version-3 lock mutation or sample
download.

Grok makes no membership classification from a symbol's spelling and does not choose a new
historical authority source in this drop. It performs no test, network/data run, migration,
integration, repository-record edit, Git operation, bulk acquisition, catalog mutation,
Nautilus work, or Harmonic Trader work. It stops for reviewer source inspection with exact
hashes and a concise change summary. Hermes remains unauthorized until that inspection.

## Publication Set

Under the reviewer governance-publication exception, the reviewer may stage, commit, and
push exactly:

- `docs/adr/0017-free-harmonic-ready-binance-derivatives-data.md`;
- `docs/handoff/CURRENT_TASK.md`;
- `research/sprint_004/98_CEX002_RESOLUTION_AND_STORAGE_ARCHITECTURE_REVIEW.md`; and
- `tickets/CEX-002.md`.

No source, test, fixture, data, generated report, database sidecar, or unrelated dirty path
belongs to this publication. The reviewer executes no tests or acceptance commands.

## Disposition

CEX-002 returns to `IN_PROGRESS`. Gate 1 has not passed. Gate 2, real bulk acquisition,
normalization, catalog publication, Nautilus execution, other-ticket work, Harmonic model
development, payoff analysis, PAPER, and LIVE remain unauthorized. Next ticket remains
`NONE`.
