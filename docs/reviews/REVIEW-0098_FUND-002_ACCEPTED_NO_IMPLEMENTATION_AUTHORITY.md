# REVIEW-0098 - FUND-002 ACCEPTED: NO IMPLEMENTATION AUTHORITY

**Ticket:** FUND-002 - Binance Funding Source Semantics Audit
**Status:** ACCEPTED - FUNDING EVENT IMPLEMENTATION BLOCKED
**Next required actor:** Jr Dev - Hermes, acceptance publication only
**Next ticket authorized:** `NONE`
**Date:** 2026-07-21

## Decision

FUND-002 is accepted with `NO_IMPLEMENTATION_AUTHORITY`.

The sampled official archives are real, bounded, checksum-verified, and reproducibly registered, but
mandatory point-in-time semantics do not pass: `calc_time` classification, interval scope, rate
unit/sign/formula, historical availability, funding-specific replacement behavior, and licensing
scope remain failed or partial.

This acceptance does not authorize a funding-rate normalizer, realized cashflows, schema, migration,
ADR, portfolio, CARRY, factor, or USD-conversion work.

## Accepted Evidence

- Three monthly USD-M funding ZIP samples and matching provider checksum sidecars.
- Four FAIL, two PARTIAL, one PASS, and one BLOCKED gate.
- Correct separation of source funding-rate events from position-dependent realized cashflows.
- Complete fail-closed recommendation: any unknown mandatory semantic prevents implementation.
- Repository control PASS; raw provider payloads remain outside Git.

## Publication Qualification

One sidecar body row still needs its own ETag, and two retained metadata/header artifacts must be
registered or removed from the source note. These do not alter the accepted semantic decision and are
restricted to `docs/reviews/FUND-002_JR_ACCEPTANCE_PUBLICATION_TASK.md`.
