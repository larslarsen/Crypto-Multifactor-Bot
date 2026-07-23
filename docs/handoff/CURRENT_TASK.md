# CURRENT_TASK

Ticket: DATA-004
State: READY
Next required actor: Sr Dev (Strong Model) — extend real market bar history
Next ticket authorized: DATA-004

**Reviewer Decision (Architecture & Ticket Selection):**

EXP-005 ACCEPTED (REVIEW-0194). Holdout: all train winners **negative OOS**. LIVE blocked.  
Store bars only **2026-01-01→2026-07-23**; EXP-004 “12m from 2025-08” is not supported by data.

Authorizing **DATA-004**: extend Binance→canonical history to ≥24 months (or document venue max); artifact `20_EXTENDED_HISTORY_REPORT.json`; `live_eligible: false`. Do not mutate 08–19.

**Policy:** No LIVE.

## Governing documents

- tickets/DATA-004.md (READY)
- tickets/EXP-005.md (ACCEPTED)
- docs/reviews/REVIEW-0194_EXP-005_ACCEPTED.md

## Acceptance (Jr)

1. .venv/bin/python -m pytest tests/execution/ tests/acquisition/ -q --tb=short
2. .venv/bin/python -m ruff check src/cryptofactors/execution src/cryptofactors/acquisition scripts/
3. 20_EXTENDED_HISTORY_REPORT.json present
4. python3 scripts/check_repo_control.py
