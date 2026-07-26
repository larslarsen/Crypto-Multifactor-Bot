# CURRENT_TASK

Ticket: DEX-002
State: ACCEPTED
Next required actor: NONE
Next ticket authorized: NONE

## Summary

DEX-002 - Screened Free DEX OHLCV Acquisition is accepted at `13000c1`.
REVIEW-0235 through REVIEW-0238 are closed by REVIEW-0239.

The accepted path enforces provider capabilities, fail-closed screening, genuine
interval bars, exact raw lineage, retry-safe watermarks, complete canonical snapshots,
and deterministic repeated refreshes. The legacy publisher and report 37 have no
authority.

## Verification

- 168 focused tests passed.
- Complete repository pytest suite passed with 6 skips.
- Scoped Ruff passed.
- Repository control passed.
- Controlled report 44 reconciles dataset
  `ds_14d5ff00c501117b200f157260bed7c2c3fda2406efa2d1eb0231218337902be`.

## Governing documents

- tickets/DEX-002.md
- docs/reviews/REVIEW-0239_DEX-002_ACCEPTED.md
