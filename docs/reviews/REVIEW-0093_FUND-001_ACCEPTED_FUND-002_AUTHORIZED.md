# REVIEW-0093 - FUND-001 ACCEPTED; FUND-002 AUTHORIZED

**Accepted ticket:** FUND-001 - Binance Funding-Cashflow Readiness
**Accepted recommendation:** `SOURCE_EVIDENCE_REQUIRED`
**Active ticket:** FUND-002 - Binance Funding Source Semantics Audit
**Next required actor:** Jr Dev - Hermes
**Next ticket authorized:** `NONE`
**Date:** 2026-07-21

## Decision

FUND-001 readiness is accepted. Accepted repository evidence establishes a source funding-rate row,
but not the mandatory unit, sign, formula, publication/availability, or funding-specific correction
semantics needed for point-in-time canonical publication.

The source layer and realized-cashflow layer are separate. A later source normalizer may emit
`funding_rate_event`; realized cashflow requires position/notional, contract formula, settlement
asset, price basis, and sign semantics downstream.

The proposed event contract remains non-governing. REF string IDs versus integer fact surrogates
remain a mapping-contract question, and source/dataset IDs remain lineage rather than logical event
identity.

## Authority

FUND-002 is authorized as the smallest next source-evidence action under
`docs/reviews/FUND-002_JR_SOURCE_SEMANTICS_AUDIT_TASK.md`.

No event implementation, realized cashflow, ADR, schema, migration, factor, portfolio, or
stablecoin-USD conversion is authorized.
