# REVIEW-0179 - PAPER-001 Factor-Driven Paper Trading Loop

**Status:** ACCEPTED
**Reviewer:** Lead Quant
**Ticket:** PAPER-001

## Findings

1. **Core loop:** `FactorDrivenPaperLoop` correctly sequences factor compute → `LongShortRankAllocator` → `PaperBroker.rebalance` under `strict_promotion_gate=True`.
2. **Fail-closed gate:** Construction without `PAPER_APPROVED` raises `UnapprovedArtifactError` (covered by test).
3. **Weights are factor-driven:** Period logs show L/S target weights from scores (not the PROMO-002 hardcoded demo). Dry-run artifact shows +4.89% equity path over 8 weeks / 32 trades.
4. **Script surface:** `scripts/run_paper_momts.py` promotes if needed, runs synthetic dry-run, writes `08_PAPER_FACTOR_LOOP_RESULTS.json`.
5. **Caveats (non-blocking):**
   - `paper_observation_reference` is `null` in the dry-run artifact: holdout path is wrapped in a broad `except` and/or observation window semantics do not complete in this fixture. Fix before LIVE promotion uses this as `paper_observation_reference`.
   - Placeholder `turnover`/`cost` on synthetic `SimulationPeriod` rows fed to `ProspectiveEvaluator` are not true period PnL increments — observation quality is degraded until fixed.

## Decision

**ACCEPT.** Factor-driven paper trading for `mod_tsmom_30_7_v1` is operational. Holdout observation hardening is a follow-up, not a block on this ticket’s primary objective.
