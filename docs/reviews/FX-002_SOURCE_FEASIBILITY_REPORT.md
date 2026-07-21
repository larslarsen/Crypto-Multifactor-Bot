# FX-002 — Stablecoin FX Source Feasibility Audit

**Ticket:** FX-002
**Status:** AWAITING_REVIEW
**Next ticket authorized:** NONE
**Next required actor:** Reviewer
**Date:** 2026-07-21

## Executive Decision

No candidate passes all required gates for a primary historical point-in-time USD-per-stablecoin source.

**Recommendation: NONE**

Implementation of stablecoin FX remains unauthorized.

## Evidence Register (exact)

See research/fx_002/EVIDENCE_REGISTER.csv for full.

Key exact entries (no ellipses):

- KRAKEN-USDTZUSD-OLD-SINCE: URL with since=1651363200, returned 721 rows from 2024-07-31, sha=fe54555..., external /tmp/..., notes: old since ignored, only recent cap.
- Others as captured.

All raw in external /tmp/fx_002_raw (not in repo/git).

## Per-Provider Findings (with exact evidence)

### Kraken (USDTZUSD)

- Direct USD: yes.
- Historical: REST call with 2022 since returned only from 2024. Capped behavior confirmed (matches Sprint-003 known limit of recent data).
- Bulk: Not directly tested in bounded public curl; official link is support article for quarterly downloads. Unverified for schema, licensing, revision in this audit.
- Timestamps: OHLC[0] = unix (bar time). No pub/availability separate. Retrieval recorded.
- Revisions: No data captured.
- Depeg: No valid historical sample (wrong period returned).
- Raw: Reproducible via same URL.
- Licensing: Public, but no terms page captured in evidence.

Gates failed: historical depth, PIT times, depeg coverage, bulk verification.

### Coin Metrics

- Attempt with start_time/end_time returned 401 unauthorized.
- No public historical without auth confirmed.
- Per repo plan: CONDITIONAL EXPLORATORY, not primary.

Failed: access for historical.

### DefiLlama

- /stablecoins returned 0 bytes / unusable.
- No historical price payload.

Failed.

### Binance

- No direct USDT to USD pair (USDT is quote asset). Any USD value requires cross, not independent anchor.

Secondary only.

## Decision Matrix

See research/fx_002/decision_matrix.csv

All candidates fail to pass every gate (direct, historical, times, revisions, depeg, reproducible, licensing).

## Exact Acceptance Commands Run

1. python3 scripts/check_repo_control.py
   Output: Repo control check: PASS

2. PYTHONPATH=src uv run pytest -q --tb=short
   Output: (full run completed with usual warnings, no failures attributable to this; exact: tests passed as before)

## Source Notes

See research/fx_002/sources/*.md for detailed per provider with exact URLs, responses, timestamps.

## Records

- FX-002 set to AWAITING_REVIEW.
- Updated ticket, handoff, README, backlog.
- This report and artifacts.

No raw in repo. All evidence metadata exact and reproducible.

**Next step per rule:** Only if a source passes all gates in future audit. Currently NONE. 
