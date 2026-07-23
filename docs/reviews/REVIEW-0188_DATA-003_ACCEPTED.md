# REVIEW-0188 — DATA-003 ACCEPTED

**Ticket:** DATA-003 — Real As-Of Path Correctness  
**Decision:** ACCEPTED  
**Prior reviews:** REVIEW-0186, REVIEW-0187 (CHANGES_REQUIRED)  
**Reviewer:** Lead Quantitative Finance Researcher/Engineer  
**Date:** 2026-07-23  
**Commits:** `e6fabac` (B1–B4), `fb2b120` (B5)

## Summary

Real as-of paper path is now structurally sound: int instrument keys, dataset resolution by type, store-root wiring, fail-closed guards, and factor-compatible adapter.

## Cleared blockers

| ID | Resolution |
|----|------------|
| B1 int keys | `PAPER_TO_INSTRUMENT_ID`, `to_instrument_id` fail-closed, `PaperSymbolAsOfAdapter` |
| B2 dataset id | `SqliteDatasetCatalog.resolve_latest_by_type("market_bars")` |
| B3 E2E market_bars | pytest mocked pipeline |
| B4 as-of close | pytest int-key + adapter |
| B5 replace_column | `set_column(idx, ...)`; test with factor field list; reviewer smoke: `make_tsmom_30_7(adapter).compute(...)` returns FactorFrame |

## Residual (non-blocking / next tickets)

- Backfill `instrument_int_id = idx+1` must stay aligned with static map (document/assert later).
- Watermark is decision-time, not bar event end.
- No mainnet multi-symbol U50 backfill evidence in-repo yet.
- Synthetic dry-run PnL ≠ real-data paper profitability gate.

## Policy

**LIVE remains blocked** until paper trading shows positive net return on **real** as-of bars (not synthetic dry-run).
