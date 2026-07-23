# PROMO-003 — PAPER_APPROVED Promotion for Frozen tsmom_14_3

**Priority:** P0  
**Status:** ACCEPTED  
**Dependencies:** PAPER-009 (ACCEPTED), PAPER-008 (ACCEPTED), PROMO-001 (ACCEPTED)  
**Layer:** promotion / registry  
**Architecture:** ADR-0008 state machine only. **No LIVE. No parameter change.**

## Objective

Register frozen model artifact `mod_tsmom_14_3_v1` (`tsmom_14_3`, lookback=14, skip=3) in the Promotion Registry and advance it through:

`RESEARCH_CANDIDATE` → `RESEARCH_ACCEPTED` → `PAPER_APPROVED`

using accepted evidence (PAPER-008 freeze + PAPER-009 PASS-bars re-validation). Pin PASS dataset `ds_0cb6415fa79119bf5317c124e9da2f0d4953b9a8d119aae45e2589ba716c5aaa`.

## Scope

1. **Register** `mod_tsmom_14_3_v1` with full `PromotionIdentityPayload` (artifact id, factor id, dataset id, risk policy, code/config versions, evidence refs).
2. **Transition** per ADR-0008:
   - RESEARCH_CANDIDATE (evidence: EXP-007 / PAPER-008)
   - RESEARCH_ACCEPTED (evidence: REVIEW-0200 / REVIEW-0202)
   - PAPER_APPROVED (evidence: PAPER-009 `26_TSMOM_14_3_PASS_BARS_PAPER.json`, REVIEW-0202)
3. **Fail closed:** do **not** transition to `LIVE_APPROVED`. Assert final state is `PAPER_APPROVED`.
4. **Artifact** `research/sprint_004/27_TSMOM_14_3_PAPER_PROMOTION.json`:
   - artifact_id, factor_id, dataset_id, quality PASS
   - promotion state trail with timestamps/event ids
   - final_state: PAPER_APPROVED
   - live_eligible: false
   - candidate_frozen: true
5. **Tests:** promotion path covered; suite green.
6. **Do not** change lookback/skip, risk limits, or bars publisher.

## Out of Scope

- LIVE_APPROVED or any live broker/order path  
- Parameter search / re-tuning  
- resolve_latest changes (already prefers PASS)

## Acceptance (Jr)

1. `.venv/bin/python -m pytest tests/promotion/ tests/execution/ -q --tb=short`
2. `.venv/bin/python -m ruff check src/cryptofactors scripts/`
3. `27_TSMOM_14_3_PAPER_PROMOTION.json` present; final_state PAPER_APPROVED; live_eligible false
4. `python3 scripts/check_repo_control.py`

## Stop Condition

After Sr: AWAITING_REVIEW, Next ticket authorized: NONE.
