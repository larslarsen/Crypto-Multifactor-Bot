# BIN-001 — Change Report: Binance archive kline normalizer

**Ticket:** BIN-001
**Source of change:** Sr Dev — Hermes in-tree edit (`src/cryptofactors/ingest/binance.py`),
no zip, no Sr commit. Integrated by Hermes (Jr Dev).
**Migration:** none.
**Integrated at:** see `git log` for the integration commit; gates below run against it.

## What changed

- `src/cryptofactors/ingest/binance.py` (new): `normalize_binance_kline` consumes
  registered `RawObject` ZIP/CSV kline archives (no network, no filename inference).
  Explicit market_type/interval/venue_id/instrument_id required. Per-object timestamp
  unit inferred from data (ms/us). Prices/volumes as Decimal. OHLC + interval validation.
  Headerless support. Surfaces malformations as typed `QualityIssue` (never silently
  repairs). Stages per-raw `bars.parquet` + `quality.parquet` with raw lineage and
  constructs a MAN-001 `PublishPlan` (source-normalized only; canonical bars are a later
  ticket, BAR-001).
- `tests/ingest/market/test_binance_kline.py` (new): 12 focused regressions covering the
  ticket's required cases.
- `pyproject.toml`: mypy override for untyped `pyarrow` (env lacks `py.typed` marker).
- Jr integration fixes to the Sr drop: empty-parquet array bug (D1), unused-import /
  ambiguous-variable lint (D2). See REVIEW-0018.

## Jr integration notes

- The Sr drop imported cleanly and all referenced symbols (audit/models,
  catalog/dataset/models, contracts, ingest/raw/paths, catalog/dataset/outputs) resolve.
- Two required cases are NOT yet implemented by the Sr drop: duplicate-open-time detection
  and gap detection (D3/D4 in REVIEW-0018). These are captured as `xfail(strict=True)`
  regressions pending Sr completion; they are not silently passed.
- No production architecture, migration, or product-test changes were made.

## Validation evidence

| Command | Result |
|---------|--------|
| `PYTHONPATH=src uv run pytest tests/ingest/market -q` | 10 passed, 2 xfailed |
| `PYTHONPATH=src uv run ruff check src/cryptofactors/ingest tests/ingest` | All checks passed |
| `PYTHONPATH=src uv run mypy --no-incremental src/cryptofactors/ingest tests/ingest` | Success (14 files) |
| `PYTHONPATH=src uv run pytest -q` (full suite) | passed |
| `python3 scripts/check_repo_control.py` | PASS |

## Status

Integrated and validated, with CHANGES_REQUIRED for duplicate/gap detection (REVIEW-0018).
BIN-001 remains `IN_PROGRESS`; `Next ticket authorized: NONE`.
