# REVIEW-0068 - AUD-005 SOURCE APPROVED; JR INTEGRATION AUTHORIZED

**Ticket:** AUD-005 - Provider-candle comparison by explicit comparable dimensions
**Status:** SOURCE APPROVED - JR INTEGRATION AUTHORIZED
**Next required actor:** Jr Dev - Hermes
**Next ticket authorized:** `NONE`
**Date:** 2026-07-20

## Decision

The local AUD-005 source is approved for Jr integration. It preserves historical all-dimension
behavior, supports explicit set/list/tuple/frozenset selection, rejects malformed selections,
requires only selected mapping fields, reports deterministic compared/not-comparable dimensions,
and keeps alignment, missing-interval, duplicate, tolerance, and mismatch contracts intact.

The Sprint-003 runner now uses canonical Binance kline indexes, excludes semantically incompatible
trade count, keeps provider raw-trade counts distinct from aggTrades record counts, and emits the
real structured comparison result.

This is source approval only. Jr Dev - Hermes owns tests, research/evidence corrections,
integration, records, commit, and push under `docs/reviews/AUD-005_JR_INTEGRATION_TASK.md`.

## Required Integration Evidence

- Prove explicit unordered-set input produces canonical deterministic metadata.
- Prove omitted input preserves the historical all-fields-required behavior.
- Cover absent unselected fields, absent selected fields, excluded mismatches, and invalid
  empty/unknown/duplicate/scalar/non-string selections.
- Exercise the Sprint-003 runner against staged Binance evidence and verify completed structured
  comparison output with corrected columns and trade-count semantics.
- Correct false `trade_count`-absent claims in Sprint-003 research records and regenerate affected
  deterministic audit outputs.
- Run all acceptance gates and record exact evidence.
