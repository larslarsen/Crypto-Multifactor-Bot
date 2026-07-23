# CURRENT_TASK

Ticket: PROMO-003
State: READY
Next required actor: Sr Dev (Strong Model) — PAPER_APPROVED promotion for frozen tsmom_14_3
Next ticket authorized: PROMO-003

**Reviewer Decision (Architecture & Ticket Selection):**

PAPER-009 ACCEPTED (REVIEW-0202). Frozen `tsmom_14_3` confirmed on PASS bars (+16.70%, zero delta). `resolve_latest` already prefers PASS. **No LIVE.**

Authorizing **PROMO-003**: register `mod_tsmom_14_3_v1` and advance RESEARCH_CANDIDATE → RESEARCH_ACCEPTED → PAPER_APPROVED only. Pin PASS dataset. Artifact `27_TSMOM_14_3_PAPER_PROMOTION.json`. `live_eligible: false`. Do **not** transition to LIVE_APPROVED.

**Policy:** No LIVE. Multiple-testing / selection-path risk still blocks LIVE_APPROVED.

## Governing documents

- tickets/PROMO-003.md
- tickets/PAPER-009.md
- docs/reviews/REVIEW-0202_PAPER-009_ACCEPTED.md
- docs/architecture/adr/0008-research-paper-live-promotion-lifecycle.md

## Acceptance (Jr)

1. .venv/bin/python -m pytest tests/promotion/ tests/execution/ -q --tb=short
2. .venv/bin/python -m ruff check src/cryptofactors scripts/
3. 27_TSMOM_14_3_PAPER_PROMOTION.json present; PAPER_APPROVED; live_eligible false
4. python3 scripts/check_repo_control.py
