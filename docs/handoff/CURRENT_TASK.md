# CURRENT_TASK

Ticket: DATA-003
State: IN_PROGRESS
Next required actor: Sr Dev (Strong Model) — fix PaperSymbolAsOfAdapter PyArrow rewrite (REVIEW-0187)
Next ticket authorized: DATA-003

**Reviewer Decision (REVIEW-0187): CHANGES_REQUIRED**

B2–B4 OK. **B5 blocker:** `PaperSymbolAsOfAdapter` calls nonexistent `table.replace_column`. Factor requests `instrument_id` in fields → real factor path broken. B4 only tested `["close"]` (false green).

## Must fix

1. Valid PyArrow column update (or skip rewrite)
2. Test adapter with `["instrument_id", "close"]` (factor field list)
3. Optional: factor compute smoke on temp bars
4. No LIVE; `live_eligible: false`

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
