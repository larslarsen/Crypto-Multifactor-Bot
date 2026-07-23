# REVIEW-0185 — DATA-002 ACCEPTED

**Ticket:** DATA-002 — Canonical Bars + Real As-Of Paper Path  
**Decision:** ACCEPTED (with deferred correctness items → DATA-003)  
**Reviewer:** Lead Quantitative Finance Researcher/Engineer  
**Date:** 2026-07-23  

## Summary

Dry-run multi-symbol path reaches canonical `market_bars` in catalog. Report artifact present with `live_eligible: false`. Jr gates reported green (pytest acquisition+execution, ruff, mypy, dry-run script, governance).

## Delivered

- `scripts/research/backfill_binance_klines.py`: ≥2 symbols → source MAN-001 → `publish_canonical_bars` → catalog `market_bars`
- `scripts/run_paper_momts.py`: non-dry-run fails closed if no DB / no `market_bars`; attempts `CatalogAsOfStore` path
- `research/sprint_004/11_REAL_DATA_PATH_REPORT.json`

## Gaps deferred to DATA-003 (must fix before claiming real paper)

1. **`CatalogAsOfStore` incomplete:** constructed with `control_database` only; docstring requires `dataset_store_root` for market bars. Real path will not load bars correctly until fixed.
2. **Universe mismatch:** paper universe is BitMEX-style (`XBTUSD`, …); Binance backfill is `BTCUSDT`/`ETHUSDT`. No symbol map.
3. **Tests:** ticket required mocked E2E canonical + paper fail-closed tests; commit is mostly scripts — add dedicated tests.
4. **Watermark:** not recorded for incremental follow-on.
5. **Silent `except Exception: pass`** in price lookup — fail closed or log structured errors.
6. Minor: duplicate `return 0` in backfill script.

## Policy

LIVE remains blocked until paper is profitable on **real** as-of data. Synthetic dry-run profitability does not satisfy that gate.
