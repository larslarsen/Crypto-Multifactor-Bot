# REVIEW-0192 — ALLOC-001 ACCEPTED

**Ticket:** ALLOC-001 — Neutrality-Preserving Risk Enforcement  
**Decision:** ACCEPTED  
**Reviewer:** Lead Quantitative Finance Researcher/Engineer  
**Date:** 2026-07-23  
**Commit:** `6901242`

## Summary

`enforce_risk_limits` now clip-then **leg-rescale** long/short independently so neutral input books stay net≈0 under 0.15 / 1.0 caps. EXP-003 clip-induced net drift is fixed for two-legged books.

## Evidence (same ~12m window as EXP-003)

| Mode | Net return | Risk | Max \|net\| on neutral books |
|------|------------|------|------------------------------|
| EXP-003 unconstrained | −5.28% | fail | ~0 |
| EXP-003 old enforce | −15.36% | pass | up to ±0.35 |
| **ALLOC-001 new enforce** | **−6.52%** | pass | ~0 when both legs; residual only one-sided frames |

Enforcement no longer destroys most of the (still negative) signal via beta leak. **LIVE still blocked** (return < 0).

## Accepted

- `risk_limits.py` neutrality-preserving algorithm + docstring
- Unit tests for clip / both-leg / directional / gross cap
- `17_NEUTRAL_RISK_SESSION.json`, runner script
- `live_eligible: false`, honest gate

## Non-blocking

- `net_exposure_tolerance` parameter is unused in body (dead API surface) — clean up later or use in assert
- One-sided factor frames still leave |net| up to 0.5 — correct per design; optional future: force flatten or pair with cash when single-sided
- Strategy still unprofitable on this sample even near unconstrained path

## LIVE policy

No LIVE. Need risk-compliant **and** positive real as-of paper before any LIVE ticket.
