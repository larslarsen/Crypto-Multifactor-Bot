# REVIEW-0191 — EXP-003 ACCEPTED

**Ticket:** EXP-003 — Risk-Compliant MOM-TS Real-Data Diagnosis  
**Decision:** ACCEPTED  
**Reviewer:** Lead Quantitative Finance Researcher/Engineer  
**Date:** 2026-07-23  
**Commit:** `0c1f423`

## Summary

Diagnosis and ~12-month real as-of paper comparison complete. **MOM-TS-01 is not LIVE-ready** under policy risk limits on this sample.

## Results (real_asof, 50 weekly decisions, 2025-08-08 → 2026-07-23)

| Mode | Max weight | Net return | meets_risk | live_gate |
|------|------------|------------|------------|-----------|
| Unconstrained | 0.50 | **−5.28%** | false | false |
| Risk-enforced (0.15/1.0) | 0.15 | **−15.36%** | true | false |

Return gap ≈ **10.1 pp** worse under enforcement — consistent with clip + flatten of concentrated ranks.

Short Apr–May 2026 unconstrained **+1.37%** (PAPER-005) does **not** generalize; longer window unconstrained is also negative.

## Accepted deliverables

- `scripts/research/diagnose_momts_risk.py` — dual session + gap/neutrality stats
- `15_MOMTS_RISK_DIAGNOSIS.json`, `16_MOMTS_LONG_SESSION.json`
- `experiment_registry.csv` EXP-003 EXECUTED
- Backfill `--report-path` (no overwrite of prior 11 report)
- `live_eligible: false` throughout

## Material engineering finding

**Dollar-neutrality drift after clip-and-renormalize** is real and large in samples (enforced net exposure up to **±0.35** while raw net ≈ 0). That injects unintended directional beta and can dominate TSMOM signal. Allocator enforcement must become **neutrality-preserving** before further edge claims.

## LIVE policy

**LIVE remains blocked.** Conditions not met: risk-compliant profitability on real as-of fails over the longer window. No LIVE ticket authorized.

## Non-blocking

- Local `exp003.db` / `data/exp003_store` not in git (OK)
- Registry is a new CSV vs EXP-002’s older registration path — acceptable for sprint_004; consolidate later if needed
- No new unit tests for diagnose script (research script; suite still green)

## Next

ALLOC-001: neutrality-preserving risk enforcement; re-measure enforced session under same data window.
