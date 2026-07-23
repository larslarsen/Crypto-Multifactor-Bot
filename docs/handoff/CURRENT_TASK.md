# CURRENT_TASK

Ticket: PAPER-001
State: READY
Next required actor: Sr Dev (Strong Model) — factor-driven paper trading loop
Next ticket authorized: PAPER-001

**Reviewer Decision (Architecture & Ticket Selection):**

Paper promotion works (`PROMO-002` / REVIEW-0178), but the demo session used **hardcoded** L/S weights. That is not production paper trading.

I am authorizing **PAPER-001** (Factor-Driven Paper Trading Loop for MOM-TS-01):
1. Wire `tsmom_30_7` → `LongShortRankAllocator` → `PaperBroker` under strict `PAPER_APPROVED` gate.
2. Dry-run path + results artifact `08_PAPER_FACTOR_LOOP_RESULTS.json`.
3. Lightweight holdout/observation snapshot for future LIVE eligibility.

No new factor families until this paper loop is real. LIVE remains blocked until paper observation evidence exists.

## Governing documents

- tickets/PAPER-001.md (READY)
- tickets/PROMO-002.md (ACCEPTED)
- docs/reviews/REVIEW-0178_PROMO-002_ACCEPTED.md

## Acceptance (Jr)

1. .venv/bin/python -m pytest tests/execution/ tests/promotion/ -q --tb=short
2. .venv/bin/python -m ruff check src/cryptofactors/execution scripts/run_paper_momts.py
3. .venv/bin/python -m mypy --no-error-summary src/cryptofactors/execution scripts/run_paper_momts.py
4. .venv/bin/python scripts/run_paper_momts.py --dry-run
5. python3 scripts/check_repo_control.py
