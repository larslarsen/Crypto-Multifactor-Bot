# CURRENT_TASK

Ticket: DATA-003  
State: READY  
Next required actor: Sr Dev (Strong Model) — real as-of path correctness  
Next ticket authorized: DATA-003  

**Reviewer Decision (Architecture & Ticket Selection):**

DATA-002 ACCEPTED (REVIEW-0185). Canonical dry-run path and report OK. Real paper path not yet trustworthy.

Authorizing **DATA-003**:
1. `CatalogAsOfStore(..., dataset_store_root=...)` + fail closed
2. Symbol map Binance ↔ paper universe
3. Required tests (E2E canonical + paper fail-closed; no bare except)
4. Watermark + correctness artifact; `live_eligible: false`

**Policy:** No LIVE. LIVE blocked until paper profitable on real as-of data.

## Governing documents

- tickets/DATA-003.md (READY)
- tickets/DATA-002.md (ACCEPTED)
- docs/reviews/REVIEW-0185_DATA-002_ACCEPTED.md

## Acceptance (Jr)

1. .venv/bin/python -m pytest tests/acquisition/ tests/execution/ -q --tb=short
2. .venv/bin/python -m ruff check src/cryptofactors/acquisition src/cryptofactors/execution scripts/
3. .venv/bin/python -m mypy --no-error-summary src/cryptofactors/acquisition src/cryptofactors/execution
4. Fail-closed tests + report
5. python3 scripts/check_repo_control.py
