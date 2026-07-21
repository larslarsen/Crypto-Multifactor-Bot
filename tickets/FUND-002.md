# FUND-002 - Binance Funding Source Semantics Audit

**Priority:** P0
**Status:** IN_PROGRESS - FINAL EVIDENCE INTEGRITY ONLY
**Recommendation:** NO_IMPLEMENTATION_AUTHORITY (source-semantics blockers)
**Dependencies:** FUND-001 readiness accepted under REVIEW-0093
**Layer:** research evidence / funding source semantics
**Architecture:** no ADR, schema, migration, or production implementation authorized

## Objective

Determine whether official Binance USD-M funding archives and documentation establish sufficient
point-in-time semantics and raw lineage for a later canonical `funding_rate_event` implementation.

## Bounded Scope

- BTCUSDT monthly funding archives for January and February 2025.
- ETHUSDT monthly funding archive for January 2025.
- Corresponding provider `.CHECKSUM` files, response headers, official documentation, replacement
  evidence, and licensing/terms evidence.

## Mandatory Gates

- `calc_time` meaning is documented precisely enough to classify event/settlement semantics.
- `funding_interval_hours` unit, effective scope, and historical change behavior are documented and
  checked against all three samples.
- `last_funding_rate` unit, sign convention, formula meaning, and relation to the event timestamp are
  documented.
- Provider publication time or a conservative historical availability bound is defensible separately
  from local retrieval time.
- Funding-specific ZIP checksums match, and replacement/correction applicability is established.
- Licensing permits the intended internal acquisition and metadata retention.
- Every conclusion is reproducible from immutable external raw captures and committed hashes.

Any unknown mandatory semantic yields `NO_IMPLEMENTATION_AUTHORITY`.

## Required Decision

Publish exactly one recommendation:

1. `EVENT_IMPLEMENTATION_AUTHORITY`; or
2. `NO_IMPLEMENTATION_AUTHORITY` with exact failed gates.

Even a passing audit cannot authorize realized funding-cashflow, portfolio, CARRY, USD-conversion,
schema, ADR, migration, or production work.

## Stop Condition

Publish evidence records, set FUND-002 to `AWAITING_REVIEW`, return control to Reviewer, retain
`Next ticket authorized: NONE`, and stop.
