# CURRENT_TASK

Ticket: UNIVERSE-006
State: AWAITING_REVIEW
Next required actor: Reviewer (Lead Quant) — review + accept
Next ticket authorized: NONE

## Sr Dev deliverables

1. Fixed `universe_at` in `src/cryptofactors/universe/cmc_survivorship.py` so inactive coins without a `death_proxy_date` are **never** eligible (fail-closed).
2. Removed row mutation in `scripts/research/publish_cmc_survivorship.py`; the published table is the raw CSV and the provider enforces the rule.
3. Re-published graveyard dataset `ds_22d2100a575a9764cceec9cc75f45867047969d1b348fd630771bfb083f5b3d8`.
4. Regenerated `research/sprint_004/42_CMC_UNIVERSE_PUBLISHED.json` with honest coverage and counts.
5. Added `test_inactive_without_death_is_excluded` in `tests/universe/test_cmc_survivorship.py`.

## Evidence

- `pytest tests/universe/test_cmc_survivorship.py` — 8/8 PASS
- `ruff check src/cryptofactors/universe/cmc_survivorship.py scripts/research/publish_cmc_survivorship.py tests/universe/test_cmc_survivorship.py` — PASS
- `scripts/check_repo_control.py` — PASS
- Report: `research/sprint_004/42_CMC_UNIVERSE_PUBLISHED.json`
  - `row_count`: 1756
  - `immortal_rows_fixed`: 153
  - `universe_at_2020_01_01_count`: 18
  - `universe_at_2026_07_01_count`: 0
  - `coverage_window.event_start`: 2013-04-28
  - `coverage_window.event_end`: 2026-07-24T19:27:58Z
  - `catalog_reconciliation.match`: true

## Governing documents

- tickets/UNIVERSE-006.md (AWAITING_REVIEW)
- docs/reviews/REVIEW-0214_UNIVERSE-006_REWORK_CHANGES_REQUIRED.md
- src/cryptofactors/universe/cmc_survivorship.py
- scripts/research/publish_cmc_survivorship.py
- research/sprint_004/42_CMC_UNIVERSE_PUBLISHED.json
