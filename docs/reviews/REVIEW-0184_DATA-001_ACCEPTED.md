# REVIEW-0184 — DATA-001 ACCEPTED

**Ticket:** DATA-001 — Live Market Data Acquisition Pipeline
**Decision:** ACCEPTED (partial scope closed; remainder split to DATA-002)
**Reviewer:** Lead Quantitative Finance Researcher/Engineer
**Date:** 2026-07-23

## Summary

Binance spot kline fetcher lands and writes through RAW-001. Normalizer + MAN-001 publish source dataset (`binance_kline_source`). Dry-run backfill verifies catalog registration. Tests pass with mocked HTTP.

## Delivered

- `src/cryptofactors/acquisition/binance_fetcher.py`
- `scripts/research/backfill_binance_klines.py` (dry-run mock path)
- `tests/acquisition/` (4 tests)
- acquisition layer in LAYER_DEPENDENCY_MATRIX

## Deferred to DATA-002

- Canonical bars publish from source datasets
- `CatalogAsOfStore` eligibility on real published bars
- Multi-symbol U50 backfill + incremental watermark
- Non-dry-run live API backfill evidence artifact

## Policy

LIVE still blocked until paper is profitable on real as-of data.
