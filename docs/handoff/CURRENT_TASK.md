# CURRENT_TASK

Ticket: UNIVERSE-003
State: ACCEPTED
Next required actor: Jr Dev (Hermes / Weak Model) — gates, records, commit, push
Next ticket authorized: NONE

**Reviewer Decision (Architecture Pivot):**
PORT-001 has been marked BLOCKED. While portfolio simulation is required for PROMO-001, honest portfolio simulation and paper promotion are structurally impossible while the universe survivorship gate (DF-08) remains red. 

The CMC backfill data prototype (`scripts/research/fetch_cmc_dead_universe.py`) is already pulled and ready. I am authorizing UNIVERSE-003 to formally ingest this CMC dead-coin graveyard. This one-shot historical backfill is a mandatory prerequisite to partially resolving DF-08 and enabling honest costed portfolio simulation and paper promotion.

## Governing documents

- tickets/UNIVERSE-003.md (ACCEPTED)
- tickets/DF-08.md (Current Blocker)

## Acceptance (Jr)

1. .venv/bin/python -m pytest tests/universe/ -q --tb=short
2. .venv/bin/python -m ruff check src/cryptofactors/universe tests/universe
3. .venv/bin/python -m mypy --no-error-summary src/cryptofactors/universe tests/universe
4. python3 scripts/check_repo_control.py
5. Test asserting provenance labels (`death_date_is_proxy`, unofficial source) are present.
