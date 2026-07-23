# CURRENT_TASK

Ticket: PROMO-001
State: ACCEPTED
Next required actor: Lead Quant (Strong Model) — next-ticket selection
Next ticket authorized: NONE

**Reviewer Decision (Authorization):**
With PORT-001 (costed portfolio simulation) accepted, all necessary upstream prerequisites (catalog, experiments, serving, and portfolio domains) for Sequence #23 are complete. 
While UNIVERSE-002 (DEX side) remains in draft, the CEX survivorship backfill (UNIVERSE-003) sufficiently resolves the DF-08 blocker for CEX-based candidate strategies. 

I am formally unblocking and authorizing **PROMO-001** (Explicit Paper Promotion, Sequence #23).

**Policy Parameters (fulfilling PROMO-001 prerequisite):**
- Prospective observation requirement: 14 days minimum before LIVE_APPROVED.
- Risk limits: Max gross leverage 1.0, single asset max weight 0.15.
- Kill-switch: Must be documented in registry schema or code before paper start.

## Governing documents

- tickets/PROMO-001.md (ACCEPTED)
- docs/handoff/IMPLEMENTATION_SEQUENCE.md

## Acceptance (Jr)

1. .venv/bin/python -m pytest tests/ -q --tb=short
2. .venv/bin/python -m ruff check src/cryptofactors tests
3. .venv/bin/python -m mypy --no-error-summary src/cryptofactors tests
4. python3 scripts/check_repo_control.py
