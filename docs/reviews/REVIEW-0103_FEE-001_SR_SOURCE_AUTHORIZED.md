# REVIEW-0103 - FEE-001 SR SOURCE AUTHORIZED

**Ticket:** FEE-001 - Point-in-Time Fee Schedules and Conservative Assumptions
**Status:** AUTHORIZED - SR SOURCE EDITS ONLY
**Assigned model:** Sr Dev - Grok Build 4.5
**Next ticket authorized:** `NONE`
**Date:** 2026-07-21

## Decision

FEE-001 is the smallest unblocked Phase 3 implementation unit. FX, funding-event, and historical
instrument-event source implementations remain blocked, while the approved architecture explicitly
permits dated fee schedules with `ASSUMED_CONSERVATIVE` evidence when history is unavailable.

Grok Build 4.5 is selected because exact Decimal persistence, bitemporal correction, migration safety,
and atomic overlap enforcement are senior production-code concerns. A cheaper model is not selected for
the source pass; its likely correction cost exceeds the bounded one-pass saving. GPT-5.4 mini will be
eligible for the later test/integration pass after Reviewer inspection.

Execute only `docs/reviews/FEE-001_SR_IMPLEMENTATION_TASK.md`. Do not edit tests or repository records,
and do not run Git commands.
