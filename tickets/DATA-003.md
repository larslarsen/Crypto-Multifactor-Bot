# DATA-003 — Real As-Of Path Correctness

**Priority:** P0  
**Status:** AWAITING_REVIEW  
**Dependencies:** DATA-002 (ACCEPTED)  
**Layer:** catalog / execution / acquisition scripts  
**Architecture:** fix wiring only; no LIVE; no new storage layer.

## Objective

Make non-dry-run paper consumption of published Binance→canonical `market_bars` actually work and be test-proven.

## Scope

1. **CatalogAsOfStore wiring** in `scripts/run_paper_momts.py` (and any helper): pass `dataset_store_root` (CLI flag defaulting to store used by backfill). Fail closed if root missing/empty for real mode.
2. **Symbol mapping:** map paper universe ids to bar keys (e.g. `XBTUSD`↔`BTCUSDT` or switch paper universe to Binance spot symbols for real mode). Document choice in report.
3. **Tests (required):**
   - Mocked E2E: fetch → RAW → normalize → MAN source → canonical → catalog assert `market_bars`
   - Paper non-dry-run fails closed without DB, without market_bars, without store root
   - Price lookup does not bare-`except` swallow all errors (assert fail-closed or typed skip with empty→error)
4. **Watermark:** record last event end (or max bar time) per symbol/dataset in report or small sidecar JSON.
5. **Artifact:** update `11_REAL_DATA_PATH_REPORT.json` or write `12_REAL_ASOF_CORRECTNESS.json` with mapping + store root + `live_eligible: false`.

## Out of Scope

- LIVE orders / LIVE_APPROVED  
- Full U50 mainnet backfill (optional ops note only)  
- New factors  

## Acceptance (Jr)

1. `.venv/bin/python -m pytest tests/acquisition/ tests/execution/ -q --tb=short`
2. `.venv/bin/python -m ruff check src/cryptofactors/acquisition src/cryptofactors/execution scripts/`
3. `.venv/bin/python -m mypy --no-error-summary src/cryptofactors/acquisition src/cryptofactors/execution`
4. Dry-run backfill + report still OK; new fail-closed tests pass
5. `python3 scripts/check_repo_control.py`

## Stop Condition

After Sr: AWAITING_REVIEW, Next ticket authorized: NONE.
