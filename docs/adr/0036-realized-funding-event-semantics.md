# ADR 0036 - Realized Funding Event Semantics

- **Status:** Accepted
- **Date:** 2026-09-02
- **Amends:** ADR-0017 section 4, ADR-0024 section 2, and ADR-0025 sections 6 and 7
- **Evidence:** `research/sprint_004/466_CEX002_REALIZED_FUNDING_ARCHITECTURE_AND_GROK_SOURCE_AUTHORIZATION.md`

## Context

CEX-002 requires `binance_usdm_funding_realized`. The accepted source is Binance's checksummed
monthly USD-M `fundingRate` archive. Each source row contains `calc_time`,
`funding_interval_hours`, and `last_funding_rate`; the accepted target schema also publishes exact
long- and short-side cashflow rates.

Funding is not an hourly state series. It is a sequence of actual settlement events, and Binance
may change a contract's funding interval. Treating an eight-hour-to-four-hour or four-hour-to-one-
hour change as a fixed grid would either manufacture settlements that never occurred or label
unobserved events as economic gaps. Dividing or multiplying the published rate by the interval
would also change the cashflow that was actually settled.

ADR-0025 already says that event-driven products use accepted object/source gaps because the
absence of an unobserved event is not an economic gap. This ADR fixes the corresponding row,
schedule-change, duplicate, and publication rules before production code is written.

## Decision

### 1. One row is one observed settlement event

`calc_time` is the event/settlement timestamp in integer Unix milliseconds. The event is usable by
a causal consumer no earlier than `calc_time`. Unknown source publication time remains unknown in
lineage and must not be copied from `calc_time` or backdated.

`funding_interval_hours` is the source-declared positive integer attached to that event. It is
preserved exactly. It describes the interval of that observed settlement; it is not permission to
infer the schedule before or after the row.

`last_funding_rate` is the exact rate settled at that event. It remains `decimal128(38,18)` and is
not annualized, divided into hourly values, rescaled for interval length, rounded, or converted
through a binary float.

### 2. Schedule changes do not create or repair rows

The normalizer publishes only observed source events. It must not expand funding events to an
hourly, four-hour, or eight-hour grid; forward-fill or interpolate rates or intervals; infer a
missing settlement solely from adjacent timestamp differences; or synthesize a zero-rate event.

An interval transition such as 8 -> 4 -> 1 -> 8 hours is valid when each positive interval is
source-declared on its observed event. The exact sequence is retained. Accepted source/object
coverage gaps remain source-coverage facts for the later typed coverage/gap product. The realized-
funding product completion binds their accepted authority but does not turn them into market rows
or a count of missing economic events.

### 3. Cashflow direction is exact and conserved

For every event:

```text
long_cashflow_rate  = -last_funding_rate
short_cashflow_rate =  last_funding_rate
long_cashflow_rate + short_cashflow_rate = 0 exactly
cashflow_sign_convention = long_pays_short_when_rate_positive
```

A positive source rate is therefore a debit to the long side and a credit to the short side. A
negative rate reverses the direction; zero produces exact zeros. These values use context-
independent exact decimal arithmetic and never include position notional, fees, or leverage.

### 4. Identity, period, ordering, and duplicate rules fail closed

The symbol in the authenticated source key is the row's venue/native symbol. Current canonical
instrument and version identifiers remain null with the accepted
`reference_identity_not_yet_created` state; a ticker-derived identity or current metadata may not
be projected backward.

Every `calc_time` must fall in the UTC month named by its authenticated monthly source key. Output
is deterministically ordered by native symbol, `calc_time`, source identity, and zero-based source
data-row ordinal. Each output row keeps its exact ordinal and partition-local raw-object reference.

Rows with the same `(native_symbol, calc_time)` and identical interval and rate represent one
economic event and may be collapsed only with all contributing source identities and ordinals
retained in lineage and an exact collapsed-row count. A repeated timestamp with a different rate
or interval is conflicting authority and fails the product. No source row is silently discarded.

### 5. Publication and completion remain immutable

The product uses the accepted 14-column typed schema and is partitioned by native symbol and the
UTC month of `calc_time`. Each partition and its complete raw-object lineage are content addressed,
published through bounded same-filesystem staging with atomic no-clobber, and hidden until one final
completion descriptor is written last. An interrupted run exposes no complete product; replay
rehashes and reuses only byte-identical winners.

Completion must bind the accepted generation-0 acquisition authority, report, sizing receipt,
schema, writer, normalizer, ordered partitions, lineages, source-gap authority, and exact equation
`physical source rows - collapsed identical rows = product rows`. Conflicting rows, excluded valid
events, inferred events, and rounded events are all zero in an accepted completion.

## Authority references

- Accepted source qualification:
  `research/sprint_004/62_CEX002_GATE1_SOURCE_PROCUREMENT.json`.
- Accepted typed sizing:
  `research/sprint_004/258_CEX002_GATE2_STORAGE_SIZING_V3.json`.
- Binance USD-M funding-rate history documentation:
  `https://developers.binance.com/docs/derivatives/usds-margined-futures/market-data/rest-api/Get-Funding-Rate-History`.
- Binance USD-M funding information documentation, including `fundingIntervalHours` adjustments:
  `https://developers.binance.com/docs/derivatives/usds-margined-futures/market-data/rest-api/Get-Funding-Rate-Info`.
- Binance public data repository:
  `https://github.com/binance/binance-public-data`.

## Consequences

- Funding interval changes are represented faithfully without inventing continuity.
- Research receives exact realized cashflow events with an explicit long/short sign convention.
- Source coverage remains honest and separate from economic-event inference.
- This ADR authorizes no acquisition, real-data run, integration, experiment, model, catalog
  transaction, Harmonic Trader work, PAPER, LIVE, or next ticket.
