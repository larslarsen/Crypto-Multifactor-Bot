# REVIEW-0190 — PAPER-006 ACCEPTED

**Ticket:** PAPER-006 — Risk-Compliant Real Paper Gate  
**Decision:** ACCEPTED  
**Reviewer:** Lead Quantitative Finance Researcher/Engineer  
**Date:** 2026-07-23  
**Commit:** `9fe8b5c`

## Summary

Paper path now enforces AUD-006-aligned limits (max single weight 0.15, gross leverage 1.0) via clip-and-renormalize before rebalance. Honest readiness gate implemented and unit-tested. Risk-compliant real as-of re-run is **unprofitable (−3.31%)** → `live_gate_satisfied: false`, `live_eligible: false`.

## Accepted deliverables

- `src/cryptofactors/execution/risk_limits.py` — `enforce_risk_limits`, `compute_live_gate_satisfied`
- `FactorDrivenPaperLoop` applies enforcement; observed risk metrics post-enforcement
- Tests for clip/scale behavior and gate truth table
- `research/sprint_004/14_RISK_COMPLIANT_PAPER_SESSION.json`
- Artifact 13 corrected: `live_gate_satisfied: false`, `superseded_by` → 14

## Material research finding (not a reject)

| Session | Risk | Net return | live_gate_satisfied |
|---------|------|------------|---------------------|
| PAPER-005 (13) unconstrained | fail (w=0.5) | +1.37% | was wrongly true; now false |
| PAPER-006 (14) enforced | pass | **−3.31%** | false (correct) |

Unconstrained “alpha” was concentration; under policy risk, edge disappears on this short window. **LIVE remains blocked.**

## Non-blocking notes

- Clip-then-scale can break dollar-neutrality when long/short magnitudes differ after clip — document in next research ticket; consider signed-renormalize later.
- Paper imports limits from `execution.live` constants — acceptable shared constants; keep live *rejection* vs paper *enforcement* distinct.
- Sample still thin (8 decisions / ~2 months). Longer real history needed before any LIVE discussion.
- `control.db` / `data/store` remain local (not in git) — re-run ops documented via scripts.

## LIVE policy (unchanged)

No LIVE until risk-compliant **and** profitable real as-of paper (plus explicit LIVE ticket). PAPER-006 does not unlock LIVE.
