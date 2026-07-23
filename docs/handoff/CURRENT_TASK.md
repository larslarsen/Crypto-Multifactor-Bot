# CURRENT_TASK

Ticket: DATA-003
State: AWAITING_REVIEW
Next required actor: Lead Quant (Reviewer) — review real as-of path correctness (REVIEW-0186 rework)
Next ticket authorized: NONE

**Reviewer Decision (REVIEW-0186): CHANGES_REQUIRED**

Fail-closed and string symbol map OK. **Real bar lookup still broken:** `CatalogAsOfStore` market keys are **int instrument_id**, not `BTCUSDT` strings. `get_real_prices` / factor path will `ValueError` or miss rows.

## Must fix

1. Symbol → int instrument_id map consistent with published bars; prices + factor
2. Dataset id resolution or explicit CLI + test
3. Pytest mocked E2E → market_bars
4. Pytest mini as-of price hit on temp publish
5. `live_eligible: false`; no LIVE

## Governing documents

- tickets/DATA-003.md (IN_PROGRESS)
- docs/reviews/REVIEW-0186_DATA-003_CHANGES_REQUIRED.md

## Acceptance (Jr)

1. .venv/bin/python -m pytest tests/acquisition/ tests/execution/ -q --tb=short
2. .venv/bin/python -m ruff check src/cryptofactors/acquisition src/cryptofactors/execution scripts/
3. .venv/bin/python -m mypy --no-error-summary src/cryptofactors/acquisition src/cryptofactors/execution
4. New E2E + as-of price tests pass
5. python3 scripts/check_repo_control.py
