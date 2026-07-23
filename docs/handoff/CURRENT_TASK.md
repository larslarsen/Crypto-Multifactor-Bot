# CURRENT_TASK

Ticket: PAPER-007
State: READY
Next required actor: Sr Dev (Strong Model) — tsmom_14_0 paper session on extended history
Next ticket authorized: PAPER-007

**Reviewer Decision (Architecture & Ticket Selection):**

EXP-006 ACCEPTED (REVIEW-0197). Multi-fold OOS corrected; best compound **tsmom_14_0** (2/3 gates). No config wins all folds. **No LIVE.**

Authorizing **PAPER-007**: risk-compliant real paper session for `tsmom_14_0` on DATA-004; artifact `22_TSMOM_14_0_PAPER_SESSION.json`; new research model id preferred; `live_eligible: false`.

**Policy:** No LIVE.

## Governing documents

- tickets/PAPER-007.md (READY)
- tickets/EXP-006.md (ACCEPTED)
- docs/reviews/REVIEW-0197_EXP-006_ACCEPTED.md

## Acceptance (Jr)

1. .venv/bin/python -m pytest tests/execution/ tests/acquisition/ -q --tb=short
2. .venv/bin/python -m ruff check src/cryptofactors/execution scripts/
3. 22_TSMOM_14_0_PAPER_SESSION.json present
4. python3 scripts/check_repo_control.py
