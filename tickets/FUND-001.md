# FUND-001 - Binance Funding-Cashflow Readiness

**Priority:** P0
**Status:** AWAITING_REVIEW
**Recommendation:** SOURCE_EVIDENCE_REQUIRED (REVIEW-0090 readiness boundary)
**Dependencies:** RAW-001/002, MAN-001, REF-001, AUD-003, RES-001 (accepted)
**Layer:** data platform / funding and costs readiness
**Architecture:** readiness only; no ADR, schema, migration, or production implementation authorized

## Objective

Determine whether accepted Binance monthly funding-archive evidence and accepted platform contracts
are sufficient to define one deterministic, point-in-time canonical funding product. Distinguish a
venue funding-rate event from a position-dependent realized cashflow.

## Accepted Inputs

- Binance monthly funding archive evidence with `calc_time`, `funding_interval_hours`, and
  `last_funding_rate`.
- Accepted RAW, MAN, REF, and source-audit contracts.
- Binance archive checksum/replacement evidence.
- Architecture requirement to store historical funding events and apply actual venue interval/sign
  conventions when booking cashflows.

## Required Questions

- What does each observed provider field prove, and which settlement/publication semantics remain
  unknown?
- Is the canonical source product a funding-rate event, a realized cashflow, or two separate layers?
- What identifies the instrument, contract version, event, raw object, source dataset, and policy?
- How are event time, publication time, retrieval time, and earliest defensible availability time
  represented without invention?
- How are rate units, interval changes, formula changes, payer/receiver sign, mark/index/notional,
  missing events, revisions, and provider file replacements handled?
- Can accepted platform contracts support the product, or would later implementation require an ADR
  or migration?
- How is native settlement value preserved while stablecoin-to-USD conversion remains blocked?

## Required Decision

Publish exactly one recommendation:

1. readiness is sufficient for a later bounded implementation ticket;
2. a named architecture decision is required first; or
3. a precise source-semantic blocker requires a narrower evidence audit.

Any proposed contract is non-governing until Reviewer acceptance. The existing
`schemas/funding_cashflow.schema.json` is an input to critique, not approved authority.

## Out Of Scope

- Provider/network calls or new raw acquisition.
- Production source, tests, schemas, migrations, generated datasets, or ADR edits.
- Fee, execution-route, portfolio, CARRY, factor, or empirical implementation.
- USD conversion or any assumption that USDT/USDC equals one USD.

## Stop Condition

Publish readiness records, set FUND-001 to `AWAITING_REVIEW`, return control to Reviewer, retain
`Next ticket authorized: NONE`, and stop.
