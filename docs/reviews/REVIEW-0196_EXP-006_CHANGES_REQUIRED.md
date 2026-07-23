# REVIEW-0196 — EXP-006 CHANGES_REQUIRED

**Ticket:** EXP-006 — Multi-Fold OOS of Frozen TSMOM Configs on Extended History  
**Decision:** CHANGES_REQUIRED  
**Reviewer:** Lead Quantitative Finance Researcher/Engineer  
**Date:** 2026-07-23  
**Commit under review:** `e5af5d6`

## Summary

Protocol shape (3 sequential test windows, frozen configs, DATA-004 dataset, `live_eligible: false`) is directionally right, but **observation / gate flags are broken for folds 1–2**, so the artifact is not trustworthy for LIVE decisions.

## Root cause (confirmed)

`ProspectiveEvaluator` sets:

- `observation_start = paper_promotion_event.payload.effective_time`
- raises if `evaluation_time < effective_time`

Research scripts register PAPER_APPROVED with **`effective_time = 2026-04-01`**.

| Fold | Test end | vs effective_time | Result |
|------|----------|-------------------|--------|
| 1 | 2025-03-31 | before | `ProspectiveHoldoutError` → `obs=None` → **risk=false, complete=false** |
| 2 | 2025-09-30 | before | same |
| 3 | 2026-07-23 | after | obs present; risk/complete can be true |

Period-log metrics in the same artifact already show fold 1–2 **max |w|=0.15, gross≤1.0** — risk enforcement ran; flags are **evaluator artifacts**, not limit breaches.

`oos_supports_live_path: true` is therefore based only on fold 3 under this broken coupling, and fold 1–2 gates are unusable.

## Additional issues

1. **Train windows unused.** `train_start`/`train_end` are recorded but never executed. Protocol is sequential test holdouts, not true expanding-window selection. Rename or implement train use; do not claim expanding-window selection.
2. **Gate return source.** `compute_live_gate_satisfied` uses full-fold `total_net_return`, while `ProspectiveEvaluator` net_return only counts periods after `effective_time`. Inconsistent for fold 3.
3. **Do not authorize LIVE** from this commit.

## Required fixes (Sr Dev)

1. **Decouple research OOS metrics from paper `effective_time`:**
   - Prefer derive `meets_risk_limits` from period logs (`max |w|`, `max gross`) with ALLOC-001 caps; and
   - derive `is_complete` from fold length / decision_count (e.g. ≥ min weeks), **or**
   - set promotion `effective_time` ≤ first decision of each fold and ensure obs window matches the fold test window.
2. **Re-run all folds** and rewrite `research/sprint_004/21_TSMOM_EXTENDED_OOS.json` only (append-only vs 08–20).
3. **Document protocol accurately** (sequential holdout vs expanding-window).
4. Keep `live_eligible: false`. Set `oos_supports_live_path` only from **corrected** per-fold gates.
5. No LIVE. No mutation of 08–20.

## Acceptance after rework

Same Jr commands as ticket EXP-006. Stop AWAITING_REVIEW, Next NONE.
