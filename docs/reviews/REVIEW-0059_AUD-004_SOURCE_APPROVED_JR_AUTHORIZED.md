# REVIEW-0059 - AUD-004 SOURCE APPROVED; JR INTEGRATION AUTHORIZED

**Ticket:** AUD-004 - Native headerless support for the Binance archive precision comparator
**Status:** SOURCE APPROVED - JR INTEGRATION AUTHORIZED
**Next required actor:** Jr Dev - Hermes
**Next ticket authorized:** `NONE`
**Date:** 2026-07-20

## Decision

The local Sr source correction is approved for Jr integration. Headerless width validation now
uses the maximum observed width across each already-bounded row sample. A short first row can reach
`_analyze` and count as malformed, while negative indices and indices absent from every sampled
row still fail closed through the existing index check.

This is source approval only, not final AUD-004 acceptance. Jr Dev - Hermes owns integration,
regression tests, acceptance gates, evidence correction, repository records, commit, and push under
`docs/reviews/AUD-004_JR_INTEGRATION_TASK.md`.

## Required Integration Evidence

- Add a regression proving a short first headerless row is governed by the malformed-rate policy
  rather than rejected before analysis.
- Use a real Binance kline column layout in kline coverage, selecting open time at index 0 or close
  time at index 6 rather than the aggTrades timestamp position.
- Preserve headed behavior, bounded-prefix extraction, archive safety, and all evidence thresholds.
- Correct the change report to match the actual tests and gate output.
