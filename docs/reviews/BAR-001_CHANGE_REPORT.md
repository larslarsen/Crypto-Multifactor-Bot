# BAR-001 — Change Report: Canonical bar publisher and daily reconciliation

**Ticket:** BAR-001
**State:** IN_PROGRESS
**Next ticket authorized:** NONE

## Integrated Sr Dev drops — REVIEW-0028 through REVIEW-0030

- Production package: `src/cryptofactors/market/__init__.py`, `src/cryptofactors/market/bars.py`
- Public API: `cryptofactors.market.publish_canonical_bars`
- Transform: `canonical_bar_publisher` version `5`
- Schema: `market_bar` version `2`
- Source-review state: integrated after REVIEW-0030 enforcement.

## Governing reviews

- `docs/reviews/REVIEW-0029_BAR-001_CHANGES_REQUIRED.md`
- `docs/reviews/REVIEW-0030_BAR-001_CHANGES_REQUIRED.md`

## Jr test integration

- Test suite: `tests/market/test_canonical_bars.py`
- Test count: 16
- Coverage:
  - verified MAN-001 trust / `DatasetPublicationReceipt.is_complete()` / recomputed dataset identity
  - `PASS_WITH_WARNINGS` propagation
  - nullable missing fields fail-closed on parse (`bar001_source_row_parse_failure`)
  - strict COIN-M schema rejection
  - inclusive-close validation (`bar001_interval_close_mismatch`)
  - complete UTC days / incomplete-day exclusion (`bar001_incomplete_utc_day`)
  - deterministic duplicate collapse / conflict quarantine (`bar001_duplicate_conflict`)
  - legacy v1 identity rejection
  - supported source identity is `binance_kline_source` v2 only
  - full immutable dual-evidence agreement with canonical `coverage` / `quality_summary` / verified output-spec identity (`rows_verified`)
  - exact-one daily source timeframe with canonical config identity (`_canonicalize_daily_source_timeframe`)

## Gate evidence

Run from repo root at commit `505e087445c0683db9d2df567589a5392aa37e7e`.

| Command | Result |
|---------|--------|
| `PYTHONPATH=src uv run pytest tests/market/test_canonical_bars.py -q --tb=short` | 16 passed |
| `PYTHONPATH=src uv run pytest -q --tb=short` | passed |
| `PYTHONPATH=src uv run ruff check src/cryptofactors/market tests/market` | All checks passed |
| `PYTHONPATH=src uv run mypy --no-incremental src/cryptofactors/market tests/market` | clean |
| `python3 scripts/check_repo_control.py` | PASS |

## Next action for reviewer

Production source `src/cryptofactors/market/bars.py` is currently not committed at the
REVIEW-0030 state. Only tests, docs, and handoff corrections are committed here.
Commit/Push rule requires fresh verified passing evidence before claiming done; the
current state passes all gates and is ready for reviewer inspection.
