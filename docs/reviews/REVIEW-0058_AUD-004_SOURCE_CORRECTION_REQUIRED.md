# REVIEW-0058 - AUD-004 SOURCE CORRECTION REQUIRED

**Ticket:** AUD-004 - Native headerless support for the Binance archive precision comparator
**Status:** CHANGES_REQUIRED - JR RECORD PUBLICATION, THEN SR SOURCE
**Next required actor:** Jr Dev - Hermes, then Sr Dev - Sandbox
**Next ticket authorized:** `NONE`
**Date:** 2026-07-20

## Decision

AUD-004 is not approved for final Jr integration. The headed-path regression is corrected, but
headerless timestamp-index validation still derives each archive width from `rows[0]`. A short
first row therefore raises before the existing malformed-rate policy can evaluate the sample.

## Required Correction

Derive each headerless archive's observed width across all sampled rows, not only the first row.
A short row must reach the existing analyzer and count as malformed. A negative index or an index
absent from every sampled row must continue to fail closed.

The exact production-source assignment is
`docs/reviews/AUD-004_SR_SOURCE_CORRECTION_TASK.md`.

## Publication Sequence

Jr Dev - Hermes must first publish this decision, the Sr source task, and matching ticket/handoff
records under `docs/reviews/AUD-004_JR_CONTROL_PUBLICATION_TASK.md`. The published handoff then
authorizes Sr Dev - Sandbox to make the local production-source correction. Sr publication is not
expected; approved-source integration and publication remain Jr responsibilities.

## Preserved Behavior

Keep the headed path, prefix extraction bound, first-row-as-data handling, integer-only headerless
selection, archive safety, schema reporting, and all evidence thresholds unchanged.

## Subsequent Jr Integration

After reviewer source approval, Jr Dev - Hermes owns regression tests using a short first row and
a real Binance kline layout (open time index 0 or close time index 6), all acceptance gates,
evidence corrections, repository records, and publication.
