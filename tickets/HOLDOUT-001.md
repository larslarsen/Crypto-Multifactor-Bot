# HOLDOUT-001 — Prospective Holdout Evaluation (Sequence #24)

**Priority:** P1
**Status:** ACCEPTED
**Dependencies:** PROMO-001, PORT-001
**Layer:** serving / evaluation
**Architecture:** implements step #24 (Prospective holdout); no new ADR required.

## Objective

Implement the Prospective Holdout evaluation engine (Sequence #24). This engine evaluates `PAPER_APPROVED` models in a strictly forward-looking, out-of-sample context. It ensures that candidates meet the 14-day minimum observation requirement and respect risk limits before they can be considered for `LIVE_APPROVED` promotion.

## Scope

- Create a `ProspectiveEvaluator` that takes a `PAPER_APPROVED` model artifact and evaluates its forward performance starting from its `effective_time`.
- Enforce the minimum observation period (e.g., 14 days). If evaluated before the period is complete, it yields an INCOMPLETE status.
- Validate the portfolio simulation output against the risk limits defined in PROMO-001 (Max gross leverage 1.0, single asset max weight 0.15).
- Output a structured `PaperObservationResult` that can be used as the `paper_observation_reference` required for the `LIVE_APPROVED` promotion gate.

## Required Contract

- Consumes the Promotion Registry to find the `PAPER_APPROVED` effective time.
- Uses `PortfolioSimulator` (PORT-001) over the out-of-sample period.
- Applies risk limit assertions.
- Returns a deterministic result containing observation duration, net return, max leverage observed, and max single-asset weight observed.

## Acceptance (Jr)

1. `.venv/bin/python -m pytest tests/serving/ -q --tb=short`
2. `.venv/bin/python -m ruff check src/cryptofactors/serving tests/serving`
3. `.venv/bin/python -m mypy --no-error-summary src/cryptofactors/serving tests/serving`
4. `python3 scripts/check_repo_control.py`

## Phased Ownership

- Sr Dev (Strong Model): logic and production source. Stop for reviewer.
- Jr Dev (Weak Model): tests, gates, records, Git, commit, push after approval.

## Stop Condition

After Sr: AWAITING_REVIEW, Reviewer next, NONE.
