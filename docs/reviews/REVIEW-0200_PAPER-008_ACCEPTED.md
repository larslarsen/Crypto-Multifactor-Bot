# REVIEW-0200 — PAPER-008 ACCEPTED

**Ticket:** PAPER-008 — Formal Paper Package for tsmom_14_3 (Freeze Candidate)  
**Decision:** ACCEPTED  
**Reviewer:** Lead Quantitative Finance Researcher/Engineer  
**Date:** 2026-07-23  
**Commit:** `10b5d87`

## Summary

Dedicated paper package for frozen **`tsmom_14_3`** / **`mod_tsmom_14_3_v1`**. Bit-matches EXP-007 full-window screen. **`candidate_frozen: true`**. **`live_eligible: false`**. No LIVE.

## Evidence

| Field | Value |
|-------|--------|
| Config | lookback=14, skip=3 |
| Window | 2024-04-01 → 2026-07-23 (121 weeks) |
| Net return | **+16.6999%** |
| Risk | max \|w\|=0.15, gross=1.0 |
| `meets_risk_limits` / derived | true / true |
| `is_complete` / derived | true / true |
| `live_gate_satisfied` | **true** |
| `live_eligible` | **false** |
| `candidate_frozen` | **true** |
| Dataset quality | REJECTED (documented) |
| Registry | PAPER-008 row in `experiment_registry.csv` |

## Accepted

- Standalone artifact `24_TSMOM_14_3_PAPER_SESSION.json`
- Freeze note forbidding further lookback/skip search without new ticket
- Cross-refs to EXP-006/007 and PAPER-007
- Runner with aligned `effective_time`

## Binding remaining LIVE blockers

1. **Selection path** — candidate chosen after multi-stage search; freeze stops further tuning, does not erase look-ahead in the research sequence.
2. **Quality REJECTED** — native 1d BAR-001 path; not LIVE-cleared data.
3. **Regime risk** — EXP-006 fold1 was negative for this config.
4. **Owner policy** — LIVE requires explicit LIVE ticket + owner authorization after blockers addressed.

## LIVE policy

**No LIVE.** Recommended next: quality-cleared bars and/or frozen forward observation — not live orders.
