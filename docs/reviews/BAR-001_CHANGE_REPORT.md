# BAR-001 — Change Report: Canonical bar publisher and daily reconciliation

**Ticket:** BAR-001
**State:** IN_PROGRESS
**Next ticket authorized:** NONE

## Integrated Sr Dev drop — REVIEW-0029 source-reviewed

- Production package: `src/cryptofactors/market/__init__.py`, `src/cryptofactors/market/bars.py`
- Public API: `cryptofactors.market.publish_canonical_bars`
- Transform: `canonical_bar_publisher` version `4`
- Schema: `market_bar` version `2`
- Source-review state: integrated after REVIEW-0029 enforcement.

## Jr integration

- Test suite: `tests/market/test_canonical_bars.py`
- Test count: 11
- Coverage: verified MAN-001 trust, PASS_WITH_WARNINGS propagation, nullable parse failures, strict COIN-M schema rejection, inclusive-close validation, incomplete UTC day exclusion, duplicate collapse/conflict quarantine, legacy v1 identity rejection.
- Alignment: supported source identity `binance_kline_source` v2, required partition metadata on manifest output specs, deterministic `dataset_id` via compute-identity, full manifest/receipt agreement, explicit source timeframe for daily resample policy.
- Authorized scope retainer: next ticket authorized = `NONE`.

## Gate evidence

Run from repo root at commit `2ee73f4b1dd0f62f7e5a5358b598c9b498d07bf9`.

| Command | Result |
|---------|--------|
| `PYTHONPATH=src uv run pytest tests/market/test_canonical_bars.py -q --tb=short` | 11 passed |
| `PYTHONPATH=src uv run pytest -q --tb=short` | passed |
| `PYTHONPATH=src uv run ruff check src/cryptofactors/market tests/market` | All checks passed |
| `PYTHONPATH=src uv run mypy --no-incremental tests/market/test_canonical_bars.py` | clean for tests; 2 pre-existing source type errors remain at `src/cryptofactors/market/bars.py:1448` from Sr drop |
| `python3 scripts/check_repo_control.py` | PASS |
