# REVIEW-0193 — EXP-004 ACCEPTED (with research caveats)

**Ticket:** EXP-004 — TSMOM Lookback Grid under Neutrality-Preserving Risk  
**Decision:** ACCEPTED  
**Reviewer:** Lead Quantitative Finance Researcher/Engineer  
**Date:** 2026-07-23  
**Commit:** `f2fd626`

## Summary

Grid executed on the EXP-003/ALLOC-001 real window with ALLOC-001 leg-rescale risk. Ticket scope met. **This is not LIVE authorization.**

## Evidence

| Rank | Config | Net return | Risk | Gate |
|------|--------|------------|------|------|
| 1 | tsmom_14_0 | **+31.12%** | pass | true |
| 2 | tsmom_14_3 | +21.72% | pass | true |
| 3 | tsmom_7_0 | +13.43% | pass | true |
| … | … | … | … | … |
| 13 | tsmom_30_7 (baseline) | **−6.52%** | pass | false |

- 14 valid cells (invalid lookback≤skip skipped)
- Baseline `30_7` matches ALLOC-001 exactly (−6.5247%) — path consistency OK
- Global and per-row `live_eligible: false`
- `recommend_live_path: true` only means “≥1 cell passed gate on this sample,” per ticket wording

## Accepted

- `scripts/research/run_tsmom_grid.py` (in-memory as-of store, grid loop, ranking)
- `research/sprint_004/18_TSMOM_GRID_RESULTS.json`
- Risk policy string: neutrality-preserving leg rescale
- No LIVE orders

## Research caveats (binding)

1. **In-sample selection / multiple testing.** All 14 configs evaluated on the **same** Aug 2025–Jul 2026 window used for prior diagnosis. Best cell (+31%) is **selected after seeing returns**. Do not treat as out-of-sample edge.
2. **No holdout / walk-forward.** Gate true on selected configs is **not** sufficient for LIVE.
3. **Artifact identity reuse.** Every cell runs under promotion id `mod_tsmom_30_7_v1` while `factor_id` varies. Fine for research smoke through paper loop; any candidate for paper/LIVE must get a **new** model artifact id and full promotion chain.
4. **Historical artifact mutation.** Commit also rewrote `08`/`09`/`10`/`12` paper ops artifacts. Those files should be immutable evidence. Git history retains originals; do not treat post-rewrite `08` as PAPER-005 baseline. Prefer append-only artifacts going forward.
5. **Warmup.** Session decisions start at `session_start` with `min_observation_days=14`; long lookbacks (60/90) may be partially cold early. Non-blocking for this research grid; fix in validation ticket if material.

## LIVE policy

**No LIVE.** `recommend_live_path` does not authorize LIVE tickets. Next step is **out-of-sample / walk-forward validation** of top configs under the same risk policy.
