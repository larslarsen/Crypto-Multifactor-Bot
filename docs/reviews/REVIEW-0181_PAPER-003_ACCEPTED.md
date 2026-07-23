# REVIEW-0181 - PAPER-003 Paper Ops Monitoring and Hardening

**Status:** ACCEPTED
**Reviewer:** Lead Quant
**Ticket:** PAPER-003

## Findings

1. **Persistence (`PaperSessionStore`):** SQLite snapshots + trade records with round-trip tests. Indexed by model/time. Adequate for paper ops MVP (ad-hoc schema outside catalog migrations is acceptable here).
2. **Loop integration:** `FactorDrivenPaperLoop` persists snapshots/trades when a store is configured; peak-equity drawdown tracking and optional `alert_callback` work (covered by drawdown test).
3. **Status artifact:** `PaperOpsMonitor` + `09_PAPER_OPS_STATUS.json` report gate status, observation ref, trade counts, and drawdown alert flag. Dry-run path wires store + monitor in `run_paper_momts.py`.
4. **Gates:** execution tests, ruff, mypy pass.

## Caveats (non-blocking follow-ups)

1. **`inspect_session` equity metrics are approximate:** `last_equity` uses `broker.get_cash()` rather than mark-to-market `get_equity(prices)`, and `peak_equity` is hardcoded to `100_000.0`. Status drawdown/net-return can be wrong when cash ≠ equity or peak moved. Fix before relying on ops alerts for capital decisions.
2. **No true session resume:** Store can load latest snapshot, but the loop does not restore broker cash/positions from the store on startup (append-only persistence only).

## Decision

**ACCEPT.** Paper ops monitoring and persistence meet the ticket’s primary objectives. Equity-metric accuracy and broker resume are follow-ups, not blockers for this acceptance.
