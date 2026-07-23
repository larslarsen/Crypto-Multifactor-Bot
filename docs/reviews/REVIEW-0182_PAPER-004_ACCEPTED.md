# REVIEW-0182 - PAPER-004 Paper Ops Equity and Resume Fixes

**Status:** ACCEPTED
**Reviewer:** Lead Quant
**Ticket:** PAPER-004

## Findings

1. **MTM equity:** `PaperOpsMonitor.inspect_session` accepts optional `current_prices` and uses `broker.get_equity(prices)` when provided; falls back to cash without prices. Tests assert cash-only vs MTM divergence after a 50% BTC rebalance.
2. **Resume:** `PaperBroker.restore_from_state` / `restore_from_store` restore cash, positions, and trade history from `PaperSessionStore`. `FactorDrivenPaperLoop` restores on init when `session_store` is set and `resume_from_store=True`.
3. **Gates:** execution tests, ruff, mypy pass.

## Caveats (non-blocking)

- `peak_equity` / `initial_cash` in the monitor remain simplified (hardcoded baseline + single-point peak). Fine for ops MVP; historical peak from snapshot series can wait for HARDEN.
- Resume does not re-validate position risk limits against current policy.

## Decision

**ACCEPT.** Both REVIEW-0181 caveats addressed. Ready for hardening phase (real as-of data / exchange stubs) under the policy: no LIVE until paper is profitable on real data.
