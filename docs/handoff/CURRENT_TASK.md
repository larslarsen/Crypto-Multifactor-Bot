# CURRENT_TASK

Ticket: EXP-008
State: READY
Next required actor: Sr Dev (Strong Model) — multiple-testing risk quantification for TSMOM grid
Next ticket authorized: EXP-008

**Reviewer Decision (Architecture & Ticket Selection):**

PROMO-003 ACCEPTED (REVIEW-0203). Frozen `tsmom_14_3` formally PAPER_APPROVED. LIVE blocked by selection-path / multiple-testing risk policy.

Authorizing **EXP-008**: formally quantify multiple-testing risk on the 14-config grid. Apply Bonferroni/FDR/bootstrap-adjusted testing. If winner survives → risk resolved, LIVE path open. If not → false discovery, archive candidate. Artifact `28_MULTIPLE_TESTING_ANALYSIS.json`. **No LIVE.**

**Policy:** No LIVE until EXP-008 resolves the selection-path risk or a new direction is authorized.

## Governing documents

- tickets/EXP-008.md
- tickets/PROMO-003.md
- docs/reviews/REVIEW-0203_PROMO-003_ACCEPTED.md
- docs/architecture/adr/0008-research-paper-live-promotion-lifecycle.md

## Acceptance (Jr)

1. .venv/bin/python -m pytest tests/ -q --tb=short
2. .venv/bin/python -m ruff check src/cryptofactors scripts/
3. 28_MULTIPLE_TESTING_ANALYSIS.json present; conclusion clear
4. python3 scripts/check_repo_control.py
