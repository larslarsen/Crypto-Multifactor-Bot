# REVIEW-0189 — PAPER-005 ACCEPTED

**Ticket:** PAPER-005 — Real As-Of Paper Session Evidence  
**Decision:** ACCEPTED (evidence accepted; LIVE gate **not** unlocked)  
**Reviewer:** Lead Quantitative Finance Researcher/Engineer  
**Date:** 2026-07-23  
**Commit:** `eeabac0`

## Summary

Non-dry-run path ran against Binance-backed canonical `market_bars` (10 symbols). Artifact `13_REAL_PAPER_SESSION.json` records `data_mode: real_asof`, +1.3745% net return over 8 weekly decisions (2026-04-11 → 2026-05-30), 80 trades, `live_eligible: false`.

## What is accepted

- Real backfill → catalog `market_bars` → paper loop on as-of path (DATA-003 stack)
- Session artifact schema and ops/harden/correctness updates
- Backfill CLI `--start-time` / `--end-time`
- Policy compliance: **no LIVE promotion** in this ticket

## Material findings (do not unlock LIVE)

1. **`meets_risk_limits: false`** — observed max single weight **0.5** vs ProspectiveEvaluator limit **0.15**; gross leverage ~1.0 OK.  
   Therefore **`live_gate_satisfied: true` is overstated** if defined as “ready for LIVE.” Positive net return alone is insufficient while risk limits fail.

2. **Thin sample** — 59 calendar days / 8 rebalances. Directionally useful; not a robust LIVE statistical gate.

3. **Evidence locality** — `control.db` and `data/store` are workspace-local (correctly not committed). Re-run needs documented commands + network.

4. **Equity = cash with 10 open L/S legs** — consistent with near-dollar-neutral MTM after rebalance; not by itself a bug.

## LIVE policy (unchanged)

LIVE remains **blocked** until, at minimum:

- `data_mode == real_asof`
- `total_net_return > 0`
- `meets_risk_limits == true`
- observation complete
- explicit LIVE ticket + reviewer authorization  

PAPER-005 does **not** satisfy the risk prong.

## Next

PAPER-006: enforce single-name / gross limits in paper allocation; redefine session `live_gate_satisfied` to require risk + return; re-run real session evidence.
