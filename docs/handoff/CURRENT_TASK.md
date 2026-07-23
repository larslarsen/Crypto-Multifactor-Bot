# CURRENT_TASK

Ticket: HARDEN-001
State: READY
Next required actor: Sr Dev (Strong Model) — paper path hardening (real as-of + venue stubs)
Next ticket authorized: HARDEN-001

**Reviewer Decision (Architecture & Ticket Selection):**

Phase order: ops fixes (done) → **hardening** → LIVE only if paper is profitable on real data.

Authorizing **HARDEN-001**:
1. Real `CatalogAsOfStore` paper path (fail closed if no data).
2. Read-only venue connectivity stub (no orders).
3. Hardening report artifact with `live_eligible: false`.

**Policy:** No LIVE promotion in this ticket. LIVE stays blocked until paper shows profitable results on real as-of data.

## Governing documents

- tickets/HARDEN-001.md (READY)
- tickets/PAPER-004.md (ACCEPTED)
- docs/reviews/REVIEW-0182_PAPER-004_ACCEPTED.md
- docs/reviews/AUD-006_RISK_REPORT.md

## Acceptance (Jr)

1. .venv/bin/python -m pytest tests/execution/ -q --tb=short
2. .venv/bin/python -m ruff check src/cryptofactors/execution scripts/
3. .venv/bin/python -m mypy --no-error-summary src/cryptofactors/execution
4. Dry-run harden report path
5. python3 scripts/check_repo_control.py
