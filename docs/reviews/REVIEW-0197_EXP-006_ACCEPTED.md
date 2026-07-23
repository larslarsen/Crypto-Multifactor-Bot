# REVIEW-0197 — EXP-006 ACCEPTED (rework)

**Ticket:** EXP-006 — Multi-Fold OOS of Frozen TSMOM Configs on Extended History  
**Decision:** ACCEPTED  
**Reviewer:** Lead Quantitative Finance Researcher/Engineer  
**Date:** 2026-07-23  
**Commits:** `e5af5d6` (initial), `8b2d233` (REVIEW-0196 rework)

## Summary

REVIEW-0196 fixed. Research OOS gates now use **period-log risk** and **decision-count completeness**, not paper `effective_time`. Protocol correctly named **`sequential_holdout`**.

## Corrected evidence (DATA-004 bars, ALLOC-001 risk)

| Config | Fold1 | Fold2 | Fold3 | Gates | All folds + |
|--------|-------|-------|-------|-------|-------------|
| tsmom_14_0 | +11.9% | −2.9% | +10.2% | 2/3 | no |
| tsmom_14_3 | −7.4% | +14.4% | +11.0% | 2/3 | no |
| tsmom_60_0 | +13.4% | −17.4% | +12.9% | 2/3 | no |
| tsmom_7_0 | −9.6% | +6.5% | −4.7% | 1/3 | no |
| tsmom_30_7 (baseline) | +21.2% | −7.0% | −5.7% | 1/3 | no |

- All cells: `meets_risk_limits=true`, `is_complete=true`, `live_eligible=false`
- `oos_supports_live_path=true` only means ≥1 fold gate; **not LIVE authorization**
- Approx compound ranking: **14_0 ≳ 14_3 ≫ 60_0**; baseline unstable

## Accepted

- Decoupled gate metrics in `run_tsmom_extended_oos.py`
- Rewritten `21_TSMOM_EXTENDED_OOS.json`
- Honest protocol note (train unused; frozen configs)

## Binding caveats

1. **No config is profitable in every fold** — regime dependence remains.
2. **Native 1d dataset still `quality_status: REJECTED`** (BAR-001) — research-usable, not LIVE-cleared.
3. **Artifact identity still `mod_tsmom_30_7_v1`** for paper-loop plumbing — any paper/LIVE candidate needs a **new** model artifact id and promotion chain.
4. **LIVE remains blocked** until a dedicated paper ticket on a chosen config is risk-compliant, complete, profitable on real data, and owner-authorized.

## LIVE policy

No LIVE from EXP-006.
