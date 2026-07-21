# AUD-004 - SR SOURCE CORRECTION TASK

**Ticket:** `tickets/AUD-004.md`
**Actor:** Sr Dev - Sandbox
**Status:** AUTHORIZED - SOURCE ONLY
**Next ticket:** `NONE`

## Assignment

Correct headerless timestamp-index validation in
`src/source_audit/binance_precision.py`.

## Required Behavior

- Derive `width_a` and `width_b` from the maximum row width observed across each already-bounded
  sample, using zero when a sample is empty.
- Allow short rows, including a short first row, to reach `_analyze` and count toward the existing
  malformed-rate threshold.
- Reject negative indices and indices absent from every sampled row.
- Preserve headed behavior and every other AUD-004 source contract unchanged.

## Scope

Production-source correction only. Jr Dev - Hermes retains tests, integration, evidence, records,
and publication ownership after reviewer source approval.

The source correction is a local source drop for reviewer inspection. Repository integration and
publication are not Sr deliverables.

## Completion Condition

Complete the minimal production-source correction for reviewer inspection.
