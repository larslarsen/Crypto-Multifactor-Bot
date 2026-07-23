# CURRENT_TASK

Ticket: PORT-001
State: READY
Next required actor: Sr Dev (Grok / Strong Model)
Next ticket authorized: PORT-001

**Reviewer Decision (Architecture):**
Sequence #22 (SERV-001) is complete. The next step is #23 (PROMO-001). However, PROMO-001 is strictly blocked by the lack of the `portfolio` domain (Sequence #15), which was skipped earlier. We cannot do explicit paper promotion without costed portfolio acceptance and portfolio/cost-model version lineage.

I am authorizing PORT-001 to implement the missing portfolio simulation layer before we can unblock PROMO-001.

## Governing documents

- tickets/PORT-001.md (READY)
- docs/handoff/IMPLEMENTATION_SEQUENCE.md

## Acceptance (Jr)

1. .venv/bin/python -m pytest tests/portfolio/ -q --tb=short
2. .venv/bin/python -m ruff check src/cryptofactors/portfolio tests/portfolio
3. .venv/bin/python -m mypy --no-incremental src/cryptofactors/portfolio tests/portfolio
4. python3 scripts/check_repo_control.py
