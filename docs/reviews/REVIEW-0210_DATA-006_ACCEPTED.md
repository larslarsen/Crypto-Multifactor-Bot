# REVIEW-0210 — DATA-006 ACCEPTED (REVIEW-0207/0209 rework)

**Ticket:** DATA-006 — Full Historical Backfill  
**Decision:** ACCEPTED  
**Reviewer:** Lead Quantitative Finance Researcher/Engineer  
**Date:** 2026-07-24  

## Summary

Option **B** rework addresses all three CHANGES_REQUIRED blockers. Spine remains: Binance 23-symbol daily bars from 2020, BitMEX funding, DEX stablecoin OHLCV, PASS quality, `live_eligible: false`.

## Blocking items (closed)

| # | Requirement | Evidence |
|---|-------------|----------|
| 1 | Ops test + registry | `bars_in_holdout_count >= 0`; `_append_registry_row` strips None keys; pytest ops green |
| 2 | Scope reduction or full depth | Option B: ticket section + reports 31–33 `scope_reduction` / `why_not_*`; artifact `34_DATA006_REVIEW0209_REWORK.json` |
| 3 | Catalog pin vs resolve_latest | `created_at` on PublishPlans; `catalog_reconciliation.match: true` on 31–33; pins equal resolve for bars/bitmex/dex |

## Code notes (accepted)

- `bars.py`: optional `created_at` so resolve_latest can prefer real timestamps (bookkeeping only).
- Backfill scripts emit scope + reconciliation on every report write.
- No LIVE; archived tsmom_14_3 untouched.

## Verification (Jr-reported + re-checked)

- pytest ops + acquisition + ingest + market — PASS  
- ruff on touched paths — PASS  
- check_repo_control — PASS  

## Binding caveats

1. History is **scoped** (2020+, U23, BitMEX 2020+, DEX ~180d). Wider runs are CLI-only follow-ons.
2. Multiple PASS siblings may exist from re-runs; consumers must pin `catalog_reconciliation.report_pinned_dataset_id`.
3. **Publication:** Sr drops are verified in the working tree; Jr must commit/push them with this acceptance (role: Jr owns Git).

## Next

Authorized: **NONE** until Lead Quant chooses next research direction on expanded data. No LIVE.
