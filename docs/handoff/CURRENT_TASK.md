# CURRENT_TASK

Ticket: INFRA-001
State: READY
Next required actor: Sr Dev (Strong Model) — daily bar refresh + paper loop scheduler
Next ticket authorized: INFRA-001

**Reviewer Decision (Architecture & Ticket Selection):**

ARCH-001 ACCEPTED (REVIEW-0205). Sprint-004 TSMOM closed as false discovery. Holdout starts 2026-07-24; no factor research until fresh bars + pre-registration.

Authorizing **INFRA-001**: automated daily bar refresh (BIN-001 → BAR-001 PASS) + optional paper step that **must not** run archived tsmom_14_3. Ops report; local cron/wrapper only. `live_eligible: false`. No LIVE.

## Governing documents

- tickets/INFRA-001.md
- tickets/ARCH-001.md
- docs/reviews/REVIEW-0205_ARCH-001_ACCEPTED.md
- research/sprint_004/29_HOLDOUT_RESERVATION.json

## Acceptance (Jr)

1. .venv/bin/python -m pytest tests/acquisition/ tests/market/ tests/execution/ -q --tb=short
2. .venv/bin/python -m ruff check src/cryptofactors scripts/
3. Ops report present
4. python3 scripts/check_repo_control.py
