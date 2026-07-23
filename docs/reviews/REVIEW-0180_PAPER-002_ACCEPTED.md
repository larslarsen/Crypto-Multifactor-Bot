# REVIEW-0180 - PAPER-002 Paper Holdout Observation Hardening

**Status:** ACCEPTED
**Reviewer:** Lead Quant
**Ticket:** PAPER-002

## Findings

1. **Period PnL:** `FactorDrivenPaperLoop` now tracks `prev_equity` and feeds true period-over-period net returns into holdout evaluation.
2. **Observed risk:** Gross leverage and max single-asset weight are measured from each period’s `target_weights` and passed into `ProspectiveEvaluator.evaluate(...)`.
3. **Evaluator API:** Optional `observed_max_leverage` / `observed_max_single_weight` replace silent stubs when provided; defaults remain for legacy callers.
4. **Error handling:** Broad bare-`except` removed; only `ProspectiveHoldoutError` and `PromotionError` suppress observation (domain-expected).
5. **Tests:** Complete window (≥14d) → non-null complete obs; short window → `is_complete=False`; 4-name book at 0.25 weight → `meets_risk_limits=False`; unapproved gate still fails closed.
6. **Dry-run:** Non-null `paper_observation_reference`; 10-name universe keeps single weight at 0.10 ≤ 0.15 so `meets_risk_limits=true` with complete 59-day window.

## Decision

**ACCEPT.** LIVE blocker from REVIEW-0179 is closed for observation identity. A future LIVE ticket may use `paper_observation_reference` from this path, subject to owner authority and kill-switch gates.
