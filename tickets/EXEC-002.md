# EXEC-002 — Live Execution Routing (Sequence #26)

**Priority:** P0
**Status:** ACCEPTED
**Dependencies:** AUD-006 (PASSED), EXEC-001 (PaperBroker), PROMO-001 (Promotion Registry)
**Layer:** execution
**Architecture:** Implements step #26 (Live Execution Routing). Requires explicit risk-board authorization (AUD-006).

## Objective

Implement a live order-routing broker that can place orders against real exchange APIs **only** for artifacts in `LIVE_APPROVED` state. This is the first component allowed to load network credentials and contact live venues.

## Hard Constraints (from AUD-006 — non-negotiable)

1. **Promotion gate:** Every order path MUST call `PromotionRegistry.get_active_promoted_artifact(id, PromotionTarget.LIVE)` and fail closed if state ≠ `LIVE_APPROVED`.
2. **No paper bleed:** Live broker MUST live in a separate module from `PaperBroker`. No shared mutable state, no inheritance of paper fills into live, no dual-mode "paper_or_live" flag.
3. **Pre-trade risk checks (before any network call):**
   - Gross leverage ≤ 1.0
   - Single-asset absolute weight ≤ 0.15
4. **Credentials:** API keys from environment only (gitignored). Never logged, never committed, never embedded in code.
5. **Kill-switch:** On any transition out of `LIVE_APPROVED` (or explicit kill), refuse new orders and surface a flatten signal. Fail closed on registry query failure.
6. **No auto-promotion:** Live broker never writes promotion events. It only reads.

## Scope

- `src/cryptofactors/execution/live.py` — `LiveBroker` with order submit / cancel / status
- Venue adapter interface (start with one venue stub or Binance-compatible REST surface; keep pluggable)
- Pre-trade risk validator shared conceptually with paper limits
- Tests using mocked HTTP (no real network in CI)

## Out of Scope

- Multi-venue smart order routing / TWAP / VWAP
- Margin / futures / leverage products beyond spot notional
- Automatic LIVE_APPROVED promotion
- Production secrets management beyond env vars

## Acceptance (Jr)

1. `.venv/bin/python -m pytest tests/execution/ -q --tb=short`
2. `.venv/bin/python -m ruff check src/cryptofactors/execution tests/execution`
3. `.venv/bin/python -m mypy --no-error-summary src/cryptofactors/execution tests/execution`
4. `python3 scripts/check_repo_control.py`
5. Test: unapproved / non-LIVE_APPROVED artifact → hard error before any HTTP call
6. Test: leverage > 1.0 or single-asset weight > 0.15 → rejected pre-trade
7. Test: mocked HTTP only (no live network in unit tests)

## Phased Ownership

- Sr Dev (Strong Model): production source only. Stop for reviewer.
- Jr Engineer (Weak Model): tests, gates, records, Git, commit, push after approval.

## Stop Condition

After Sr: AWAITING_REVIEW, Next ticket authorized: NONE.
