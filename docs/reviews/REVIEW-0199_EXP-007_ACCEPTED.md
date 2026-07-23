# REVIEW-0199 — EXP-007 ACCEPTED

**Ticket:** EXP-007 — Full-Window Paper Screen of Remaining Multi-Fold Candidates  
**Decision:** ACCEPTED  
**Reviewer:** Lead Quantitative Finance Researcher/Engineer  
**Date:** 2026-07-23  
**Commit:** `bc16365`

## Summary

Same continuous full-window protocol as PAPER-007. **`tsmom_14_3` is the first risk-compliant profitable full-window result.** LIVE still not authorized.

## Evidence (2024-04-01 → 2026-07-23, 121 weeks)

| Config | Model id | Net return | Risk | Complete | Gate |
|--------|----------|------------|------|----------|------|
| **tsmom_14_3** | mod_tsmom_14_3_v1 | **+16.70%** | true | true | **true** |
| tsmom_60_0 | mod_tsmom_60_0_v1 | −15.44% | true | true | false |
| tsmom_30_7 | mod_tsmom_30_7_v2 | −27.92% | true | true | false |
| tsmom_14_0 (PAPER-007) | mod_tsmom_14_0_v1 | −0.63% | true | true | false |

- `any_fullwindow_gate: true`
- Global `live_eligible: false`
- Distinct artifact ids; `effective_time` = first decision
- DATA-004 pin + quality REJECTED documented

## Accepted

- Screen runner + `23_TSMOM_FULLWINDOW_SCREEN.json`
- Honest ranking; baseline included

## Binding caveats (LIVE)

1. **Multiple-testing / selection path.** Configs survived grid → short OOS → multi-fold → full-window screen. `14_3` was not pre-registered as the sole candidate before seeing full-window results. Gate true ≠ pre-registered edge.
2. **Fold inconsistency.** EXP-006 fold1 for `14_3` was **−7.4%** (gate false). Full-window average masks regime risk.
3. **Dataset quality REJECTED** (native 1d BAR-001). Not LIVE-cleared data quality.
4. **`live_eligible: false` remains** until a dedicated LIVE ticket after owner policy + quality path + (recommended) frozen forward observation.

## LIVE policy

**No LIVE ticket from EXP-007.** Next step: formal single-config paper package for `tsmom_14_3` and freeze for any forward work — still not LIVE.
