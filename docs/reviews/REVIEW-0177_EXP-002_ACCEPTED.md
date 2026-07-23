# REVIEW-0177 - EXP-002 MOM-TS-01 Perpetual Execution and Results

**Status:** ACCEPTED
**Reviewer:** Lead Quant
**Ticket:** EXP-002

## Findings

1. **Runner Wiring:** `momts_runner.py` correctly redirects both `run_30_7` and `run_90_7` to `run_perpetual_experiment`. The bundles have been correctly updated to use `portfolio_cell = "perp_ls"` and `portfolio_version = "perp_ls_v1"`.
2. **Metrics Mapping:** `MOMTSRunnerResult` correctly consumes the expanded output from `PerpetualSimulationResult` (liquidations, long/short return attribution, total funding cost) and exposes them for the final artifact generation.
3. **Execution Script:** `scripts/run_momts_experiments.py` implements the full pipeline. Crucially, it wires up the `BitMEXFundingProvider` properly when running with a real control DB, while cleanly falling back to a synthetic engine with a mocked funding provider and synthetic price histories for dry runs. 
4. **Registrations:** The status of both experiments in `05_EXPERIMENT_REGISTRATIONS.csv` correctly advanced to `EXECUTED`.
5. **Gates:** Pytest, Ruff, Mypy (on target files), and repo control all pass.

## Decision

**ACCEPT.** The MOM-TS-01 factor (30-7 and 90-7 variants) is fully operationalized and mechanically executable under realistic perpetual L/S constraints.
