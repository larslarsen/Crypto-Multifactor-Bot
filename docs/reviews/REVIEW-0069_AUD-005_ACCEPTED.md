# REVIEW-0069 - AUD-005 FINAL REVIEW: ACCEPTED

**Ticket:** AUD-005 - Provider-candle comparison by explicit comparable dimensions
**Status:** ACCEPTED - CLOSING PUBLICATION AUTHORIZED
**Next required actor:** Jr Dev - Hermes
**Next ticket authorized:** `NONE`
**Date:** 2026-07-20

## Decision

AUD-005 is accepted. `compare_bars` now supports explicit, validated comparable dimensions while
preserving historical all-dimension behavior when selection is omitted. Selected provider fields
remain fail-closed, unselected fields are not required, and deterministic result metadata reports
both compared and non-comparable dimensions.

The Sprint-003 runner uses the authoritative Binance kline layout, compares OHLC and base/quote
volume, excludes semantically incompatible trade count, and never equates provider raw-trade count
with aggTrades archive-record count.

## Acceptance Evidence

- Focused bar suite: 23 passed.
- Sprint-003 runner suite: 6 passed.
- Ruff: passed.
- Scoped strict mypy: passed for 13 source files.
- Full pytest suite: 430 passed, 1 warning.
- Repository control: passed.
- Regenerated structured bar-comparison and execution-manifest evidence is published.
- Sprint-003 execution and research-lead records contain the corrected trade-count semantics.

## Accepted Boundaries

- No `OHLCVBar` optionality or schema migration was introduced.
- Interval alignment, missing intervals, duplicate reporting, Decimal tolerances, and mismatch
  signs remain unchanged.
- Default calls retain all-fields-required behavior.
- Explicit empty, unknown, duplicate, scalar, and non-string selections fail closed.
- `trade_count_tolerance` is not overloaded to conceal semantic incompatibility; explicit
  dimensions control comparison scope.

## Publication

Jr Dev - Hermes owns accepted-state publication under
`docs/reviews/AUD-005_JR_ACCEPTANCE_PUBLICATION_TASK.md`. No next ticket is authorized.
