# REVIEW-0195 — DATA-004 ACCEPTED (with quality caveat)

**Ticket:** DATA-004 — Extend Real Market Bar History for Credible OOS  
**Decision:** ACCEPTED  
**Reviewer:** Lead Quantitative Finance Researcher/Engineer  
**Date:** 2026-07-23  
**Commit:** `a68bb3c`

## Summary

Extended Binance spot **1d** history for the 10-name paper universe through RAW→MAN→canonical path. Span **2024-01-01 → 2026-07-23** (~**30.7 months**, ≥24 required). `live_eligible: false`.

## Evidence

| Field | Value |
|-------|--------|
| `canonical_dataset_id` | `ds_a17651d5c871656f18c29d50fe96d41fa9f08eee8436b276237f96a679764dcd` |
| `bar_start` / `bar_end` | 2024-01-01 / 2026-07-23 |
| `span_months` | 30.69 |
| `total_bar_count` | 9350 (10 × 935) |
| per-symbol gaps | 0 |
| `venue_max_reached` | false |
| Spot-check closes | Real-looking (e.g. BTC ~44k Jan 2024), not mock ramp |
| `data_mode` | `real_asof` (not dry-run) |

Append-only: only `20_*.json` + runner. Prior datasets retained.

## Accepted

- `scripts/research/extend_binance_history.py`
- `research/sprint_004/20_EXTENDED_HISTORY_REPORT.json`
- Span gate met

## Binding caveats

1. **`quality_status: REJECTED`** — BAR-001 flags native `1d` sources with `unsupported_daily_interval` (daily promotion expects sub-day tiling). Same structural outcome as the prior short `market_bars` set used in EXP-003–005. Research as-of path still reads `market_bars/intraday/.../timeframe=1d` parquet. **Do not treat REJECTED as “fake data.”** Do treat it as **not quality-cleared for LIVE**.
2. Future hardening (separate ticket): feed **1h** (or valid sub-day) klines and promote proper daily bars, or extend BAR-001 native-daily acceptance with explicit policy.
3. `resolve_latest_by_type("market_bars")` now returns the **new** extended dataset — subsequent OOS must pin this id in artifacts.

## LIVE policy

**No LIVE.** Data extension only; no strategy validation in this ticket.
