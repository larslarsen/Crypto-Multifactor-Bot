# BAR-001 — Change Report: Canonical bar publisher and daily reconciliation

**Ticket:** BAR-001
**State:** IN_PROGRESS
**Next ticket authorized:** NONE

## Integrated Sr Dev drop — REVIEW-0027 v2 source-reviewed

- Production package: `src/cryptofactors/market/__init__.py`, `src/cryptofactors/market/bars.py`
- Public API: `cryptofactors.market.publish_canonical_bars`
- Transform: `canonical_bar_publisher` version `2`
- Schema: `market_bar` version `2`
- Source-review status: integrated; production defect found in REVIEW-0028.

## REVIEW-0028 blocking source finding

- `src/cryptofactors/market/bars.py:1425` unpacks `_extract_verified_identity` into 3 targets, but the helper returns 4 values. This breaks any `publish_canonical_bars(..., native_daily=...)` call at runtime. See `docs/reviews/REVIEW-0028_BAR-001_CHANGES_REQUIRED.md`.
- BAR-001 remains `IN_PROGRESS`; Jr integration blocked until Sr Dev ships corrected source.

## Integration

- `tests/market/test_canonical_bars.py`: 12 focused regressions covering:
  - verified manifest/receipt trust, empty manifest SHA rejection
  - PASS_WITH_WARNINGS propagation
  - nullable missing fields fail-closed on parse (`source_row_parse_failure`)
  - strict COIN-M schema rejection
  - inclusive-close validation
  - complete vs incomplete UTC days
  - deterministic duplicate collapse / conflict quarantine
  - valid lineage (`ds_`-prefixed dataset IDs)
  - daily reconciliation mismatch/missing-native/missing-resampled issue codes
  - MAN-002 PublishPlan identities and `verify_outputs`
  - deterministic config hash
  - transform/schema version brakes v2

## Gate evidence

Run from repo root at gate commit `e285700142c9f41172821c1a3cb1b19aad731467`.

| Command | Result |
|---------|--------|
| `PYTHONPATH=src uv run pytest tests/market -q --tb=short` | 12 passed |
| `PYTHONPATH=src uv run pytest -q --tb=short` | passed |
| `PYTHONPATH=src uv run ruff check src/cryptofactors/market tests/market` | All checks passed |
| `PYTHONPATH=src uv run mypy --no-incremental tests/market/test_canonical_bars.py` | clean for tests |
| `python3 scripts/check_repo_control.py` | PASS |

## Git artifacts

- Gate commit: `e285700142c9f41172821c1a3cb1b19aad731467`
- Test function count in file: 12
- Source bug blocked: `docs/reviews/REVIEW-0028_BAR-001_CHANGES_REQUIRED.md`
