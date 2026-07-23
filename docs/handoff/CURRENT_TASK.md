# CURRENT_TASK

Ticket: DATA-003
State: AWAITING_REVIEW
Next required actor: Lead Quantitative Finance Researcher/Engineer (reviewer)
Next ticket authorized: NONE

**Reviewer Decision (REVIEW-0187): CHANGES_REQUIRED**

B2–B4 OK. **B5 blocker:** `PaperSymbolAsOfAdapter` calls nonexistent `table.replace_column`. Factor requests `instrument_id` in fields → real factor path broken. B4 only tested `["close"]` (false green).

## Fixed

1. `PaperSymbolAsOfAdapter._maybe_translate_instrument_id` now uses `pyarrow.Table.set_column` (valid PyArrow API) instead of nonexistent `replace_column`.
2. Added `test_adapter_translates_instrument_id_with_factor_field_list` in `tests/execution/test_paper_asof_real.py` querying `["instrument_id", "close"]` via the adapter and asserting translated string `instrument_id` and finite `close`.
3. No LIVE; `live_eligible: false` retained.

## Governing documents

- tickets/DATA-003.md (IN_PROGRESS)
- docs/reviews/REVIEW-0187_DATA-003_CHANGES_REQUIRED.md
- docs/reviews/REVIEW-0186_DATA-003_CHANGES_REQUIRED.md

## Acceptance (Jr)

1. .venv/bin/python -m pytest tests/acquisition/ tests/execution/ -q --tb=short
2. .venv/bin/python -m ruff check src/cryptofactors/acquisition src/cryptofactors/execution scripts/
3. .venv/bin/python -m mypy --no-error-summary src/cryptofactors/acquisition src/cryptofactors/execution
4. New adapter/factor-field test passes
5. python3 scripts/check_repo_control.py
