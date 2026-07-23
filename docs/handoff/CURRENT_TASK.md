# CURRENT_TASK

Ticket: EXP-005
State: READY
Next required actor: Sr Dev (Strong Model) — OOS / walk-forward TSMOM validation
Next ticket authorized: EXP-005

**Reviewer Decision (Architecture & Ticket Selection):**

EXP-004 ACCEPTED (REVIEW-0193). In-sample grid: best `tsmom_14_0` **+31.12%**, baseline `30_7` **−6.52%**. Multiple-testing risk high. **No LIVE.**

Authorizing **EXP-005**: holdout or walk-forward validation of frozen top configs + baseline; artifact `19_TSMOM_OOS_VALIDATION.json`; `live_eligible: false`. Do not mutate artifacts 08–17.

**Policy:** No LIVE. In-sample `recommend_live_path` is not authorization.

## Governing documents

- tickets/EXP-005.md (READY)
- tickets/EXP-004.md (ACCEPTED)
- docs/reviews/REVIEW-0193_EXP-004_ACCEPTED.md

## Acceptance (Jr)

1. .venv/bin/python -m pytest tests/execution/ tests/acquisition/ -q --tb=short
2. .venv/bin/python -m ruff check src/cryptofactors/execution scripts/
3. 19_TSMOM_OOS_VALIDATION.json present
4. python3 scripts/check_repo_control.py
