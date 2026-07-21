# REVIEW-0066 - AUD-005 SCHEMA CORRECTED; SR SOURCE AUTHORIZED

**Ticket:** AUD-005 - Provider-candle comparison by explicit comparable dimensions
**Status:** RESOLVED - SUPERSEDED BY REVIEW-0067/0068/0069
**Next required actor:** Jr Dev - Hermes, then Sr Dev - Sandbox
**Next ticket authorized:** `NONE`
**Date:** 2026-07-20

## Decision

AUD-005 is authorized with a corrected Binance premise. The repository's canonical 12-column
kline schema defines close time at index 6, quote volume at index 7, and provider trade count at
index 8. The Sprint-003 runner currently maps index 6 as quote volume and omits index 8.

The provider count is nevertheless not comparable to reconstructed `trade_count`: the
reconstruction counts aggTrades archive records, while the kline field counts provider raw trades.
AUD-005 must support explicit semantic exclusion and report `trade_count` as not comparable. It
must never claim that the provider field is absent or substitute the aggregate-record count.

## Approved Contract

- Add an explicit, validated set of comparable bar dimensions with deterministic canonical order:
  open, high, low, close, base volume, quote volume, and trade count.
- Preserve historical behavior when no explicit set is supplied: all dimensions remain required
  and compared.
- For an explicit set, require every selected provider field and do not access unselected optional
  fields. Unknown or empty selections fail closed.
- Always retain interval alignment, missing-interval, and duplicate reporting independently of
  selected value dimensions.
- Report deterministic `compared_dimensions` and `not_comparable_dimensions` in
  `BarComparisonResult`.
- In the Sprint-003 runner, compare OHLC, base volume, and quote volume; exclude trade count;
  parse quote volume from column 7; and describe column-8 provider trade counts as available but
  semantically distinct from aggTrades record counts.
- Emit the real structured comparison result rather than nonexistent summary attributes.

No schema migration or architecture expansion is authorized. The local source assignment is
`docs/reviews/AUD-005_SR_SOURCE_TASK.md`.

**Resolution:** REVIEW-0066 corrected the Binance schema premise and authorized Sr Dev - Sandbox
source work. The source was corrected under REVIEW-0067, approved under REVIEW-0068, integrated
under the Jr integration task, and accepted under REVIEW-0069. AUD-005 is closed.
