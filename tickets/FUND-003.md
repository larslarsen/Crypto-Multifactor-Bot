# FUND-003 - OKX Funding Archive Source Semantics Audit

**Priority:** P0
**Status:** IN_PROGRESS
**Recommendation:** PENDING
**Dependencies:** FEE-001 accepted (fee-schedule substrate available)
**Layer:** research evidence / funding source semantics
**Architecture:** no ADR, schema, migration, or production implementation authorized

## Objective

Determine whether official OKX historical funding module 3 archives and documentation establish
sufficient point-in-time semantics and raw lineage for a later canonical `funding_rate_event`
implementation.

## Bounded Scope

- 2022-05-01 historical archive (allswap-fundingrates-2022-05-01.zip).
- April 2025 funding-formula transition boundary (formulaType: noRate -> withRate).
- 2026-07-19 archive-to-current-REST correspondence (allswap-fundingrates-2026-07-19.zip vs
  api.okx.com/api/v5/public/funding-rate).
- At least one documented variable-interval instrument (4h funding for select altcoin swaps).
- Corresponding provider response headers, ETag/Content-MD5, official documentation, and
  licensing/terms evidence.

## Mandatory Gates

- `fundingTime` meaning is documented precisely enough to classify event/settlement semantics.
- `fundingRate`/`realizedRate` unit, sign convention, formula meaning, and relation to the event
  timestamp are documented.
- `formulaType` effective scope and historical change behavior are documented and checked against
  all samples.
- Funding interval derivation from `fundingTime`/`nextFundingTime` is documented; variable-interval
  instruments are accounted for.
- Provider publication time or a conservative historical availability bound is defensible separately
  from local retrieval time.
- Archive integrity (ETag/Content-MD5) is verified; replacement/correction applicability is
  established.
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

Publish evidence records, set FUND-003 to `AWAITING_REVIEW`, return control to Reviewer, retain
`Next ticket authorized: NONE`, and stop.
