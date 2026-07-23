# DATA-002 — Canonical Bars + Real As-Of Paper Path

**Priority:** P0
**Status:** ACCEPTED
**Dependencies:** DATA-001 (ACCEPTED), BAR-001 / market bars stack, ASOF catalog, PAPER-004, HARDEN-001
**Layer:** market / catalog / execution
**Architecture:** use existing `publish_canonical_bars`, `DatasetPublisher`, `CatalogAsOfStore`. No new storage layer. **No LIVE.**

## Objective

Close the gap from DATA-001 source datasets to factor/paper consumption on real as-of bars.

## Scope

1. **Source → canonical bars**
   - From a published `binance_kline_source` dataset (or staged equivalent), build `VerifiedSourceBarDataset` and call `publish_canonical_bars`.
   - Publish canonical result via MAN-001 `DatasetPublisher`; register in catalog.
   - Extend `scripts/research/backfill_binance_klines.py` (or add sibling) so dry-run ends with a non-empty canonical `market_bars` (or project-canonical type) dataset in catalog.

2. **As-of store wiring**
   - Document/implement how `CatalogAsOfStore` loads the published canonical dataset id.
   - `scripts/run_paper_momts.py` non-`--dry-run` path: fail closed if no real bars; when DB+dataset present, use as-of closes (not synthetic).

3. **Minimal multi-symbol path**
   - Support ≥2 symbols in backfill dry-run (or one real API smoke if network allowed in CI-off path).
   - Watermark field or last-event timestamp recorded for incremental follow-on (simple is fine).

4. **Artifact**
   - `research/sprint_004/11_REAL_DATA_PATH_REPORT.json` with dataset ids, row counts, data_mode, `live_eligible: false`.

5. **Tests**
   - Mocked end-to-end: fetch → RAW → normalize → MAN source → canonical → catalog assert.
   - Paper path fails closed without real dataset.
   - No order placement.

## Out of Scope

- LIVE promotion / funded orders
- Full U50 historical backfill on mainnet (may be ops run after merge)
- WebSocket streaming

## Acceptance (Jr)

1. `.venv/bin/python -m pytest tests/acquisition/ tests/execution/ -q --tb=short`
2. `.venv/bin/python -m ruff check src/cryptofactors/acquisition src/cryptofactors/execution scripts/research/`
3. `.venv/bin/python -m mypy --no-error-summary src/cryptofactors/acquisition src/cryptofactors/execution`
4. Dry-run backfill (or new script) produces canonical dataset in catalog + report artifact
5. `python3 scripts/check_repo_control.py`

## Stop Condition

After Sr: AWAITING_REVIEW, Next ticket authorized: NONE.
