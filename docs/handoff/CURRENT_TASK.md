# CURRENT_TASK

Ticket: ARCH-001
State: READY
Next required actor: Sr Dev (Strong Model) — archive false discovery, establish pre-registered single-test framework
Next ticket authorized: ARCH-001

**Reviewer Decision (Architecture & Ticket Selection):**

EXP-008 ACCEPTED (REVIEW-0204). tsmom_14_3 is a false discovery by all four multiple-testing corrections. **Candidate archived. No LIVE.**

Authorizing **ARCH-001**: archive the false-discovery candidate in the Promotion Registry (REJECTED/RETIRED), reserve a holdout period from the dataset, and establish a pre-registration template for single-hypothesis factor tests. `29_HOLDOUT_RESERVATION.json`. `tickets/templates/PRE_REGISTERED_TEST.md`. No new factors or backtests.

**Policy:** No LIVE.

## Governing documents

- tickets/ARCH-001.md
- tickets/EXP-008.md
- docs/reviews/REVIEW-0204_EXP-008_ACCEPTED.md
- docs/architecture/adr/0008-research-paper-live-promotion-lifecycle.md

## Acceptance (Jr)

1. .venv/bin/python -m pytest tests/ -q --tb=short
2. .venv/bin/python -m ruff check src/cryptofactors scripts/
3. 29_HOLDOUT_RESERVATION.json present
4. tickets/templates/PRE_REGISTERED_TEST.md present
5. python3 scripts/check_repo_control.py
