# BAR-001 — Change Report: Canonical bar publisher and daily reconciliation

**Ticket:** BAR-001
**State:** IN_PROGRESS
**Next ticket authorized:** NONE

## Integrated Sr Dev drop

- Production package: `src/cryptofactors/market/__init__.py`, `src/cryptofactors/market/bars.py`
- Public API: `cryptofactors.market.publish_canonical_bars`
- Transform: `canonical_bar_publisher` version `1`
- Schema: `market_bar` version `1`
- Source-review status: integrated; no additional production changes in this integration.

## Integration

- `tests/market/test_canonical_bars.py`: 13 focused regressions covering:
  - REJECTED/QUARANTINED source datasets fail closed
  - PASS / PASS_WITH_WARNINGS promote to canonical
  - exclusive `period_end` and `availability_time` from `open_time + interval`
  - stable sort + uniqueness quarantine on duplicate `(instrument, venue, timeframe, period_start)`
  - daily resample across UTC midnight
  - native daily reconcile: mismatch → quarantine report
  - COIN-M volume mapping, no false quote label
  - partition layout `venue_id`/`market_type`/`timeframe`/`year`/`month`
  - MAN-001 `PublishPlan` identities and deterministic output specs
  - required `code_commit`; rejects `""` and `"unknown"`
  - deterministic explicit/config `config_sha256` derivation
  - canonical constant identity

## Gate evidence

Run from repo root at gate capture commit `b881335817e9390011a37afb73b522d985746416`.

| Command | Result |
|---------|--------|
| `PYTHONPATH=src uv run pytest tests/market -q --tb=short` | 13 passed |
| `PYTHONPATH=src uv run pytest -q --tb=short` | passed |
| `PYTHONPATH=src uv run ruff check src/cryptofactors/market tests/market` | All checks passed |
| `PYTHONPATH=src uv run mypy --no-incremental src/cryptofactors/market tests/market` | Success |
| `python3 scripts/check_repo_control.py` | PASS |

## Git artifacts

- Gate commit: `b881335817e9390011a37afb73b522d985746416`
- Test function count in file: 13
