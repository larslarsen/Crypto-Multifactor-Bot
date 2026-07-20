# BAR-001 — Change Report: Canonical bar publisher and daily reconciliation

**Ticket:** BAR-001
**State:** IN_PROGRESS
**Next ticket authorized:** NONE

## Sr Dev source-reviewed

- Production package: `src/cryptofactors/market/__init__.py`, `src/cryptofactors/market/bars.py`
- Public API: `cryptofactors.market.publish_canonical_bars`
- Transform: `canonical_bar_publisher` version `5`
- Schema: `market_bar` version `2`

## Jr work-in-progress

- Test suite: `tests/market/test_canonical_bars.py`
- Test count: 11
- Current test contract: transform v3, schema v2 legacy path plus v2-v4 BAR behavior
- Source contract: transform v5 with REVIEW-0028/0029/0030 identity changes
- Gap note: REVIEW-0030 adds coverage / quality_summary / output-spec / daily-timeframe
  canonicalization identity requirements not yet asserted by tests.

## Gate evidence

| Command | Result |
|---------|--------|
| `PYTHONPATH=src uv run pytest tests/market/test_canonical_bars.py -q --tb=short` | 11 passed |
| `PYTHONPATH=src uv run pytest -q --tb=short` | passed |
| `PYTHONPATH=src uv run ruff check src/cryptofactors/market tests/market` | All checks passed |
| `PYTHONPATH=src uv run mypy --no-incremental src/cryptofactors/market tests/market` | clean |
| `python3 scripts/check_repo_control.py` | PASS |
