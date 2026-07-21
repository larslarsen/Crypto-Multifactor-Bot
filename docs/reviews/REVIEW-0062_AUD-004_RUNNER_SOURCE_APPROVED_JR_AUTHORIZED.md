# REVIEW-0062 - AUD-004 RUNNER SOURCE APPROVED; JR AUTHORIZED

**Ticket:** AUD-004 - Native headerless support for the Binance archive precision comparator
**Status:** SOURCE APPROVED - JR INTEGRATION AUTHORIZED
**Next required actor:** Jr Dev - Hermes
**Next ticket authorized:** `NONE`
**Date:** 2026-07-20

## Decision

The local REVIEW-0061 runner correction is approved for Jr integration. The successful native
comparison result is converted with `asdict`, and only its two float threshold fields are replaced
with exact `Decimal` values at the runner boundary. This preserves every result field while keeping
the global no-float serializer and source-audit model contracts unchanged.

This is source approval only. Final AUD-004 acceptance requires successful integration and complete
gate evidence under `docs/reviews/AUD-004_JR_FINAL_INTEGRATION_TASK.md`.

## Required Integration Evidence

- Integrate the approved local runner correction without broadening it.
- Add the archive-B malformed and sampled-row assertions still missing from the REVIEW-0060
  regression.
- Demonstrate that the Sprint-003 runner serializes a completed native precision result.
- Run every focused and full acceptance gate and record exact outcomes.
- Correct all ticket, handoff, backlog, README, and change-report state/evidence inconsistencies.
