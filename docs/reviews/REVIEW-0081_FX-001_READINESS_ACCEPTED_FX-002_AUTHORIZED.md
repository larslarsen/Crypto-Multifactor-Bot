# REVIEW-0081 - FX-001 READINESS ACCEPTED; FX-002 AUTHORIZED

**Ticket:** FX-001 - Point-in-Time Stablecoin FX Readiness
**Status:** READINESS ACCEPTED - IMPLEMENTATION BLOCKED
**Next active ticket:** FX-002
**Next required actor:** Jr Dev - Hermes
**Next ticket authorized:** `NONE`
**Date:** 2026-07-20

## Decision

FX-001 readiness is accepted only for these repository-grounded conclusions:

- stablecoin FX is a P0 prerequisite;
- REF already supports `FIAT`/`STABLE` asset classes and instrument base/quote IDs;
- generic manifest publishing can represent a future Parquet dataset without storing observations
  in SQLite;
- no source is currently accepted for point-in-time stablecoin/USD FX;
- implementation, ADR, and migration work must remain blocked until source authority is established.

The proposed observation schema in `FX-001_READINESS_REPORT.md` is not approved. It uses integer
types for string REF IDs, leaves observation identity and partitioning alternative-filled, reverses
or ambiguously states rate direction, conflates raw and dataset lineage IDs, omits an exact policy
identity, and provides placeholder rather than exact phase commands. Those details are non-governing
until source evidence exists and a later reviewer decision defines them.

FX-002 is authorized as the single smallest next action under
`docs/reviews/FX-002_JR_SOURCE_AUDIT_TASK.md`.
