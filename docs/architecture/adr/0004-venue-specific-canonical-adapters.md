# ADR-0004 — Venue-specific canonical adapters

**Status:** Accepted

## Decision

Write thin venue/provider-specific acquisition and normalization adapters. A unified third-party exchange library may be used for diagnostics, but it is not the canonical source of timestamp, units, or contract semantics.

## Rationale

Research correctness depends on details that unifying libraries can hide: volume units, funding intervals/signs, contract multipliers, bar closure, pagination, and schema changes.

## Consequences

- More explicit adapter code.
- Smaller blast radius when one source changes.
- Raw payloads and official schema meaning remain auditable.
