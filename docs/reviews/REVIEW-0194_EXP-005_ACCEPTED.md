# REVIEW-0194 — EXP-005 ACCEPTED (with caveats)

**Ticket:** EXP-005 — OOS / Walk-Forward Validation of Top TSMOM Configs  
**Decision:** ACCEPTED  
**Reviewer:** Lead Quantitative Finance Researcher/Engineer  
**Date:** 2026-07-23  
**Commit:** `b8ada68`

## Summary

Holdout protocol executed under ALLOC-001 risk. Train-selected winners **all lose on the test fold**. `oos_supports_live_path: false`. **No LIVE.**

## Evidence

| Config | Train (8 wk) | Test (7 wk) | Test gate |
|--------|--------------|-------------|-----------|
| tsmom_14_0 | +5.63% | **−5.85%** | false |
| tsmom_60_0 | +3.45% | **−4.62%** | false |
| tsmom_14_3 | +1.72% | **−9.56%** | false |
| tsmom_30_7 (baseline) | −3.13% | **−6.23%** | false |

- Protocol: holdout_split; no lookback/skip re-optimization on test
- Global + per-row `live_eligible: false`
- Append-only: only `19_*.json` + runner (no 08–17 mutation in this commit)

## Data reality check (binding)

Canonical `market_bars` in `exp003` span **2026-01-01 → 2026-07-23** only (~2244 rows).  
EXP-005 defaults (train from 2026-04-08 after ~90d warmup) are **consistent with available data**.

EXP-004’s claimed session start **2025-08-08** is **not supported by this store** (pre-2026 decisions had no bars). Treat EXP-004 full-window ranks as **contaminated / not comparable** to a true 12m backtest. Prefer EXP-005’s shorter honest window for LIVE decisions.

## Accepted

- `scripts/research/run_tsmom_oos_validation.py`
- `research/sprint_004/19_TSMOM_OOS_VALIDATION.json`
- Correct negative OOS conclusion

## Non-blocking gaps

1. **Ticket listed frozen EXP-004 top-3 including `tsmom_7_0`.** Implementation re-selected top-3 on the train fold (`14_0`, `60_0`, `14_3`) + baseline; **`tsmom_7_0` not OOS-tested.** Acceptable scientifically (selection only on train); if `7_0` is ever proposed again, require OOS first.
2. **Module docstring** still describes 2025-08 → 2026-01 train; **CLI defaults differ**. Fix docstring on next touch.
3. **Statistical power is thin** (8 + 7 weekly decisions). Failure to find OOS edge is informative but not a high-powered rejection of all TSMOM.

## LIVE policy

**No LIVE.** In-sample EXP-004 winners do not survive holdout. Baseline remains negative. Extend history before further TSMOM promotion claims.
