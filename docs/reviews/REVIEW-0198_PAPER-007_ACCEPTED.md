# REVIEW-0198 — PAPER-007 ACCEPTED

**Ticket:** PAPER-007 — Risk-Compliant Paper Evidence for tsmom_14_0  
**Decision:** ACCEPTED  
**Reviewer:** Lead Quantitative Finance Researcher/Engineer  
**Date:** 2026-07-23  
**Commit:** `56592b8`

## Summary

Full-window real as-of paper session for **`tsmom_14_0`** on DATA-004 under ALLOC-001 risk. New model id **`mod_tsmom_14_0_v1`**. **Not profitable → LIVE blocked.**

## Evidence

| Field | Value |
|-------|--------|
| Window | 2024-04-01 → 2026-07-23 (121 weekly decisions) |
| Net return | **−0.6286%** |
| Final equity | 99,371.38 on 100k |
| max \|w\| / gross | 0.15 / 1.0 |
| max \|net\| | 0.5 (one-sided residual) |
| `meets_risk_limits` | true |
| `is_complete` | true |
| `live_gate_satisfied` | **false** |
| `live_eligible` | **false** |
| Dataset quality | REJECTED (native 1d BAR-001 caveat; documented) |

## Accepted

- New artifact id (not reuse of `mod_tsmom_30_7_v1`)
- `effective_time` aligned to first decision (avoids EXP-006 obs trap)
- Risk-enforced continuous path (not fold-restart compound)
- Honest gate / no LIVE

## Research interpretation (binding)

1. EXP-006 multi-fold showed **2/3** positive folds for `14_0`; **continuous full-window paper is slightly negative**. Fold restarts ≠ path-dependent continuous equity. **Paper session is authoritative for LIVE policy.**
2. Multi-fold optimism does **not** clear LIVE.
3. Residual max \|net\|=0.5 on one-sided books remains by design (ALLOC-001).

## LIVE policy

**No LIVE.** Need risk-compliant **and** profitable continuous real paper before any LIVE ticket.
