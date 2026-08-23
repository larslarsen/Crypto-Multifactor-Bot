# ADR 0025 - Complete Product Sizing and Fee Authority

- **Status:** Accepted
- **Date:** 2026-08-23
- **Amends:** ADR-0017, ADR-0021, and ADR-0024
- **Evidence:** `research/sprint_004/233_CEX002_TYPED_SIZING_CORRECTION_REVIEW.md`

## Context

ADR-0024 replaced a generic string envelope and a duplicate release-tree allocation with
typed product sizing and partition-atomic publication. Static review of the first
correction exposed two different problems: implementation defects in the correction and
parts of the final product contract that were never fixed tightly enough for a maximum
Gate-3 allocation.

The accepted qualification report contains 106 logical sample records for 96 unique raw
objects. Ten physical keys are intentionally repeated across sample roles with identical
lineage and different regime labels. It also contains 8,317 product-scoped
`universe_coverage_gaps` and 3,742 product/symbol typed-gap memberships. These are existing
authority facts, not future estimates.

The required cost product includes effective fee schedules. CEX-002 qualified the bounded
book-ticker/depth sample but retained no fee-schedule authority, and the current FEE-001
control table has zero rows. Binance's documented `/fapi/v1/commissionRate` endpoint is a
signed, current, account-specific query; it is not historical fee authority. No source or
research assumption may be silently substituted for an effective-dated schedule.

## Decision

### 1. Reopen the incomplete source boundary

Gate 1's accepted Binance archive, contract-membership, Coinalyze, raw-byte, checksum, and
sample results remain valid. Gate 1 is nevertheless incomplete for the release as a whole
because the required effective-fee component has no accepted source authority.

Before another sizing source drop, the reviewer must do one of the following through a
separate evidence-backed decision:

1. qualify a free, reproducible effective-dated fee source with retrieval and availability
   semantics; or
2. prove that no such source is available and amend the research contract explicitly.

A current account rate, current public fee page, remembered VIP-0 number, test fixture,
hard-coded constant, or current value projected backward is not historical authority.
Gate 2 remains blocked and bulk acquisition remains unauthorized.

### 2. Distinguish target products from measurement components

Physical-family contribution schemas are measurement intermediates. They do not by
themselves constitute the required product schema. The next sizing design must pin the
complete target schema for all eleven ticket products, including:

- canonical instrument and contract-version identity in membership and gap rows;
- total and taker-buy flow inputs plus the derived sell and imbalance fields the trade-flow
  product publishes;
- OI level/change semantics, realized-funding interval and cashflow convention,
  premium/indicative fields, and causal mark/index/basis fields;
- observed/censored liquidation units and side convention;
- fee-schedule fields as well as every retained quote/depth field in cost calibration;
- product-scoped coverage counts and gap intervals; and
- every dataset, manifest, schema, mapping, source/code/config identity, unit convention,
  censorship flag, and intersection count required by the final bundle descriptor.

The receipt may conservatively sum independently measured physical contributions, but it
must separately identify and bound every target-only or derived field. A statement that a
field is derivable is not a storage allocation for the field the normalizer must publish.

### 3. Exact conversion is context independent

Fixed-decimal representability must be decided from the source lexeme's sign, coefficient,
and exponent using integer arithmetic. It may not depend on Python's ambient decimal
context, use a binary float, or round. Reconstruction of the fixed-scale value must also be
context independent. Exponent, scale, and precision overflow must become redacted
`SizingError` failures.

Timestamp conversion likewise uses integer calendar arithmetic relative to the UTC epoch;
`datetime.timestamp()` is not an exact-integer implementation contract.

### 4. Accepted aliases are folded, conflicts are rejected

Lineage binding groups report sample records by physical source key. Repeated logical roles
are valid only when SHA-256, byte size, family, retrieval time, availability semantics, and
source-availability time agree exactly. Those agreeing aliases fold to one physical
lineage record while retaining all logical role labels. A disagreement, missing binding,
or second checkpoint object still blocks.

For the accepted authority, this rule must reproduce exactly 106 logical records and 96
unique physical bindings. Rejecting every repeated key makes the accepted input
unexecutable and is forbidden.

### 5. Manifest payload and overhead are partition local

For every required product/symbol/UTC-month partition, lineage storage is:

1. the sum of conservative per-mapping payload charges for every raw object feeding that
   partition, including repeated cross-product references;
2. row-group/footer metadata for that partition's manifest; and
3. fixed Parquet framing for that partition's manifest.

A whole cohort manifest divided by its row count is not this equation. Coinalyze partitions
follow the same rule: each symbol/month partition maps its local raw reference to the real
or projected response receipt and the proved provider/native identity. Payload, overhead,
mapping count, and largest partition are published separately.

### 6. Coverage storage starts from the full accepted matrix

The coverage/gap product may not be sized from the 202 Coinalyze non-mappings alone. Its
known minimum is the accepted report's 8,317 product-scoped `universe_coverage_gaps`, with
their actual product, family, symbol, kind, status, and interval semantics.

The later Gate-3 quality path must also fit row-level gaps. For every fixed-cadence target
partition with an expected-row ceiling `N`, sizing reserves up to `ceil(N / 2)` missing-run
records, the maximum number of disjoint missing intervals in an ordered expected grid.
Event-driven products use their accepted object/source gaps because absence of an
unobserved event is not an economic gap. Known source gaps and projected quality-gap rows
are separately reported and never replaced by a catalog-page count.

### 7. Cadence ceilings use the fastest permitted interval

Daily metrics remains fixed at 300 seconds. Realized funding may not be fixed at eight
hours: the retained schema carries `funding_interval_hours`, and Binance has published
four-hour contracts and a standard one-hour adjustment rule. Until a stricter proved
historical lower bound exists, the conservative funding calendar ceiling is one hour.
Every contribution publishes the observed-ratio bound, calendar bound, and winning bound.

## Authority references

- Accepted local qualification report:
  `research/sprint_004/62_CEX002_GATE1_SOURCE_PROCUREMENT.json`.
- Binance USD-M `User Commission Rate` documentation:
  `https://developers.binance.com/en/docs/catalog/core-trading-derivatives-trading-usd-s-m-futures/api/rest-api/account#user-commission-rate`.
  It documents a signed current query with `symbol` and request `timestamp`, not an
  effective-time or history range.
- Binance's STRK launch notice records a four-hour USD-M funding schedule:
  `https://www.binance.com/en-TR/support/announcement/detail/2bfb6f8dccf447ada57165b7e6a4cf1b`.
- Binance's funding-frequency explanation describes the standard one-hour adjustment rule:
  `https://academy.binance.com/ur-PK/articles/how-to-trade-stock-perpetual-contracts-on-binance`.

## Consequences

- Claude's review-232 correction cannot be integrated or executed.
- The accepted version-1 receipt and all accepted source evidence remain immutable.
- No developer is authorized until the reviewer closes the effective-fee source decision
  and publishes a complete correction contract.
- This does not authorize a paid source, reduced universe, price-only study, data download,
  normalization, Harmonic Trader work, backtest, PAPER, or LIVE work.
