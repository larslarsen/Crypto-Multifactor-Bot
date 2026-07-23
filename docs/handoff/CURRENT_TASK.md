# CURRENT_TASK

Ticket: DATA-002
State: READY
Next required actor: Sr Dev (Strong Model) — canonical bars + real as-of paper path
Next ticket authorized: DATA-002

**Reviewer Decision (Architecture & Ticket Selection):**

DATA-001 ACCEPTED (REVIEW-0184). Fetcher → RAW-001 → MAN-001 source path works. Canonical bars, as-of eligibility, and real paper path deferred.

Authorizing **DATA-002**:
1. Source dataset → `VerifiedSourceBarDataset` → `publish_canonical_bars` → MAN-001
2. Wire `CatalogAsOfStore` / paper non-dry-run to real published bars (fail closed)
3. Report artifact `11_REAL_DATA_PATH_REPORT.json` with `live_eligible: false`
4. Tests: mocked E2E + paper fail-closed

**Policy:** No LIVE. LIVE blocked until paper profitable on real data.

## Governing documents

- tickets/DATA-002.md (READY)
- tickets/DATA-001.md (ACCEPTED)
- docs/reviews/REVIEW-0184_DATA-001_ACCEPTED.md

## Acceptance (Jr)

1. .venv/bin/python -m pytest tests/acquisition/ tests/execution/ -q --tb=short
2. .venv/bin/python -m ruff check src/cryptofactors/acquisition src/cryptofactors/execution scripts/research/
3. .venv/bin/python -m mypy --no-error-summary src/cryptofactors/acquisition src/cryptofactors/execution
4. Dry-run canonical dataset + report
5. python3 scripts/check_repo_control.py
