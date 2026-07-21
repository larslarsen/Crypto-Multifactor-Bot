# REVIEW-0090 - FUND-001 READINESS AUTHORIZED

**Prior ticket:** FX-002 accepted under REVIEW-0089
**Active ticket:** FUND-001 - Binance Funding-Cashflow Readiness
**Status:** AUTHORIZED - READINESS ONLY
**Next required actor:** Jr Dev - Hermes
**Next ticket authorized:** `NONE`
**Date:** 2026-07-21

## Decision

FUND-001 is the smallest repository-grounded P0 continuation. Accepted Binance evidence already
contains historical funding-rate rows and replacement-aware archive lineage, while canonical event,
availability, interval, sign, formula, and cashflow boundaries remain unresolved.

FX implementation remains blocked. PROMO-001 remains blocked. No factor, universe, serving, or live
work is authorized.

## Readiness Boundary

The current `schemas/funding_cashflow.schema.json` is non-governing. It conflicts with accepted REF
string identifiers and does not establish whether its row represents a provider funding event or a
portfolio-dependent cashflow. FUND-001 must resolve or explicitly block those semantics before any
production implementation.

Jr Dev - Hermes is authorized only under `docs/reviews/FUND-001_JR_READINESS_TASK.md`.
