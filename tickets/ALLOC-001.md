# ALLOC-001 — Neutrality-Preserving Risk Enforcement

**Priority:** P0  
**Status:** ACCEPTED  
**Dependencies:** EXP-003 (ACCEPTED), PAPER-006 (ACCEPTED)  
**Layer:** execution / portfolio  
**Architecture:** fix `enforce_risk_limits` (and paper loop usage). **No LIVE.**

## Objective

EXP-003 showed clip-and-renormalize drives **net exposure** from ~0 to ±0.35 while capping single-name weight. Replace with a policy that:

1. Caps `|w_i| ≤ max_single_weight` (0.15)
2. Caps gross `sum|w_i| ≤ max_gross_leverage` (1.0)
3. **Preserves dollar neutrality** when the unconstrained book was neutral (net ≈ 0): post-enforcement `|sum w_i|` within a small tolerance (e.g. 1e-6), or document irreducible residual when impossible

## Scope

1. **Algorithm** (choose and document in module docstring + tests):
   - Preferred: clip per name, then **separately rescale long and short legs** to restore equal long/short gross (or target net=0) while respecting single-name and total gross caps.
   - Fail closed or reduce gross further if infeasible — never silently leave |net| >> 0 when input was neutral.

2. **Wire** into `FactorDrivenPaperLoop` (already calls `enforce_risk_limits`).

3. **Tests**
   - Neutral L/S book with one leg needing clip → post net ≈ 0, max |w| ≤ 0.15, gross ≤ 1.0
   - Asymmetric book that cannot stay neutral under caps → documented behavior (error or max residual) with test
   - Existing risk/gate tests still pass (update expectations if needed)

4. **Re-run evidence** (same universe/window as EXP-003 if local data present, else dry-run synthetic + note):
   - `research/sprint_004/17_NEUTRAL_RISK_SESSION.json` with enforced metrics, net exposure stats, `live_eligible: false`
   - Optional update diagnosis pointer in registry

## Out of Scope

- LIVE promotion  
- Changing TSMOM factor definition  
- Changing 0.15 / 1.0 policy constants  

## Acceptance (Jr)

1. `.venv/bin/python -m pytest tests/execution/ -q --tb=short`
2. `.venv/bin/python -m ruff check src/cryptofactors/execution scripts/`
3. `.venv/bin/python -m mypy --no-error-summary src/cryptofactors/execution`
4. Artifact `17_NEUTRAL_RISK_SESSION.json` with `live_eligible: false`
5. `python3 scripts/check_repo_control.py`

## Stop Condition

After Sr: AWAITING_REVIEW, Next ticket authorized: NONE.
