# CURRENT_TASK

Ticket: EXP-002
State: AWAITING_REVIEW
Next required actor: Lead Quant (Reviewer) — review MOM-TS-01 perpetual execution wiring and script
Next ticket authorized: NONE

**Reviewer Decision (Architecture & Ticket Selection):**

To actually execute `EXP-2026-019` and `EXP-2026-020`, we need to wire the new `PerpetualSimulator` (from PORT-002) into the `momts_runner.py`'s main entry points (`run_30_7` and `run_90_7`), which are currently still pointing at the spot placeholder. 

Furthermore, we need a concrete execution script (`scripts/run_momts_experiments.py`) that loads the environment, the funding provider, and executes the backtest over the decision times, outputting the metrics (liquidations, long/short attribution, net return) required by the registration.

I am authorizing **EXP-002** (MOM-TS-01 Perpetual Execution and Results) to complete this final wiring and execution step.

## Governing documents

- tickets/EXP-002.md (READY)
- docs/handoff/IMPLEMENTATION_SEQUENCE.md
- research/sprint_004/05_EXPERIMENT_REGISTRATIONS.csv

## Acceptance (Jr)

1. .venv/bin/python -m pytest tests/experiments/ -q --tb=short
2. .venv/bin/python -m ruff check src/cryptofactors/experiments scripts/
3. .venv/bin/python -m mypy --no-error-summary src/cryptofactors/experiments scripts/
4. python3 scripts/check_repo_control.py
