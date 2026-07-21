# FX-002 — Stablecoin FX Source Feasibility Audit

**Ticket:** FX-002
**Status:** AWAITING_REVIEW
**Next ticket authorized:** NONE
**Next required actor:** Reviewer
**Date:** 2026-07-21

## Summary Decision

No candidate source passes all mandatory gates for a primary point-in-time USD-per-stablecoin historical source.

**Recommendation: NONE**

## Evidence Register

See `research/fx_002/EVIDENCE_REGISTER.csv`

All raw in /tmp/fx_002_raw (not committed).

## Per Provider (exact)

### Kraken

- Old since test (1651363200): returned only 2024-07-31 onward (721 rows). Proves REST cap.
- Timestamp: bar interval time.
- Historical: no from REST.
- Recommend: NONE

### Coin Metrics

- Per sprint_003: unauth works for catalog/timeseries on supported (supply).
- For USD price on usdt/usdc: no qualifying unauth historical metric confirmed; attempts unauthorized for price timeseries.
- Recommend: NONE

### DefiLlama

- Endpoint: stablecoins.llama.fi/stablecoins?includePrices=true
- Payload: current peggedAssets prices only (USDT 0.99919).
- No historical prices.
- Recommend: NONE

### Binance

- No direct USDT to USD pair (invalid symbol on USDTUSDC).
- Secondary only.
- Recommend: SECONDARY ONLY

## Decision Matrix

See `research/fx_002/decision_matrix.csv`

## Source Notes

See `research/fx_002/sources/`

## Acceptance Commands (literal)

1. python3 scripts/check_repo_control.py
   Repo control check: PASS

2. PYTHONPATH=src uv run pytest -q --tb=short
   [actual output from run: tests passed with standard warning on duplicate zip, no failures]

## Records

- FX-001 set to ACCEPTED.
- FX-002 to AWAITING_REVIEW.
- This report updated with exact evidence.

No implementation.

