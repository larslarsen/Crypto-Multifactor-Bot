# BAR-001 — Change Report: Canonical bar publisher and daily reconciliation

**Ticket:** BAR-001
**State:** IN_PROGRESS
**Next ticket authorized:** NONE

## Source-reviewed Sr drops

- Production package: `src/cryptofactors/market/__init__.py`, `src/cryptofactors/market/bars.py`
- Public API: `cryptofactors.market.publish_canonical_bars`
- Working-tree transform: `canonical_bar_publisher` version `5`
- Worked schema: `market_bar` version `2`
- Next source requirements: `docs/reviews/REVIEW-0030_BAR-001_CHANGES_REQUIRED.md`

## Jr test integration

- Test suite: `tests/market/test_canonical_bars.py`
- Test count: `16`
- Tests:
  - verified MAN-001 trust / DatasetPublicationReceipt.is_complete / recomputed dataset id
  - pass_with_warnings propagation
  - nullable missing fields fail-closed on parse
  - strict COIN-M schema rejection
- Paths:
  - inclusive-close validation
  - complete UTC day / incomplete-day exclusion
  - deterministic duplicate collapse / conflict quarantine
  - legacy v1 identity rejection
  - supported source identity is binance_kline_source v2 only
  - full immutable dual-evidence agreement with canonical coverage / quality_summary / output-spec rows_verified identity
  - exact-one daily source timeframe with canonical config identity

## Gate evidence

Run from repo root at commit `c8157b65bfd83b77b56de8f824ad71639edc0a0a`.

| Command | Result |
|---------|--------|
| `PYTHONPATH=src uv run pytest tests/market/test_canonical_bars.py -q --tb=short` | `16 passed` |
| `PYTHONPATH=src uv run pytest -q --tb=short` | `passed` |
| `PYTHONPATH=src uv run ruff check src/cryptofactors/market tests/market` | `All checks passed!` |
| `PYTHONPATH=src uv run mypy --no-incremental src/cryptofactors/market tests/market` | `clean` |
| `python3 scripts/check_repo_control.py` | `PASS` |

## Open source item

Production source `src/cryptofactors/market/bars.py` is at the Review 0030 state in the working tree.
