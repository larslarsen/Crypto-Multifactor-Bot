# BIN-001 — Change Report: Binance archive kline normalizer (v2)

**Ticket:** BIN-001
**Source of change:** Sr Dev — Grok Build source-only drop (`BIN-001_SR_REVIEW0019_FIXES.md`);
no zip, no Sr commit. Integrated by Hermes (Jr Dev).
**Migration:** none.
**Integrated at:** `d40ecea` / current HEAD.

## What changed

- `src/cryptofactors/ingest/binance.py` (v2, `BINANCE_KLINE_TRANSFORM_VERSION = "2"`):
  inclusive-close validation (`open_time + interval - 1`), UTC-microsecond normalization,
  duplicate-open-time and gap quality issues (within + cross-object), MAN-001 row
  counters (`REQUIRE_VERIFIER`), market-type validation/aliases (`spot`/`usdm`/`coinm`)
  with volume semantics, calendar-month intervals (`1M`/`1mo`), malformed-first-row
  handling, and explicit header skip only for `open_time`/`opentime`.
- `tests/ingest/market/test_binance_kline.py`: 12 focused regressions covering the
  ticket's required cases against the v2 behavior.

## Jr integration notes

- Patched Sr v1 empty-parquet bug and lint (unused imports/ambiguous `l`) already
  present; v2 retains the empty-path fix from prior integration.
- Updated acceptance gate paths in `tickets/BIN-001.md` from nonexistent
  `src/cryptofactors/ingest/market` to the actual `src/cryptofactors/ingest` and
  `tests/ingest/market` paths.
- No production architecture, migration, or unrelated product changes made.

## Validation evidence

| Command | Result |
|---------|--------|
| `PYTHONPATH=src uv run pytest tests/ingest/market -q --tb=short` | 12 passed |
| `PYTHONPATH=src uv run ruff check src/cryptofactors/ingest tests/ingest/market` | All checks passed |
| `PYTHONPATH=src uv run mypy --no-incremental src/cryptofactors/ingest tests/ingest/market` | Success (14 files) |
| `PYTHONPATH=src uv run pytest -q` (full suite) | passed |
| `python3 scripts/check_repo_control.py` | PASS |

## Status

Integrated and validated. BIN-001 remains `IN_PROGRESS`; `Next ticket authorized:
NONE`.
