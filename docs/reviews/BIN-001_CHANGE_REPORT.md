# BIN-001 — Change Report: Binance archive kline normalizer

**Ticket:** BIN-001
**State:** IN_PROGRESS
**Next ticket authorized:** NONE

## Integrated source drop

- Source drop from Sr Dev — Grok Build local filesystem edit (no zip, no Sr commit).
- Integrated production file: `src/cryptofactors/ingest/binance.py`
- Transform: `BINANCE_KLINE_TRANSFORM_VERSION = "3"`
- Schema: `BINANCE_KLINE_SCHEMA_VERSION = "2"`
- Review history reviewed during integration:
  - `docs/reviews/REVIEW-0018_BIN-001_CHANGES_REQUIRED.md`
  - `docs/reviews/REVIEW-0019_BIN-001_CHANGES_REQUIRED.md`
  - `docs/reviews/REVIEW-0020_BIN-001_CHANGES_REQUIRED.md`
  - `docs/reviews/REVIEW-0021_BIN-001_INTEGRATION_CHANGES_REQUIRED.md`
  - `docs/reviews/REVIEW-0022_BIN-001_INTEGRATION_CHANGES_REQUIRED.md`

## Integration evidence from Jr Dev

- `tests/ingest/market/test_binance_kline.py` contains 25 focused regressions:
  - inclusive-close ms/us + exclusive-close mismatch
  - per-row mixed-unit normalization with normalized UTC-microsecond values plus preserved `source_timestamp_unit`
  - invalid timestamp issue + `CoverageWindow` exclusion/inclusion bounds
  - within/cross-object duplicate and gap detection with scope lineage
  - empty and header-only fail-closed
  - malformed first row not silently treated as header
  - calendar month `1M` month-end and leap-year `2020-02-29` bar
  - case-sensitive `1m` vs `1M`
  - spot/USD-M/COIN-M physical volume columns plus partition units
  - unknown market rejection
  - complete `PublishPlan` MAN-001 verification
  - actual `DatasetPublisher.publish` with temp catalog/store; current v3 fails manifest validation
  - raw-object lineage on every output partition
  - local-only operation via package resource lookup
- Corrected ticket acceptance command paths in `tickets/BIN-001.md`
  (`src/cryptofactors/ingest/market` → actual `src/cryptofactors/ingest` /
  `tests/ingest/market`).
- Removed brittle hard-coded checkout path from `test_no_network_used`.
- No independent production source changes beyond Sr drop integration.

## Final integration record — REVIEW-0022 response

| Finding from REVIEW-0022 | Integration action |
|--------------------------|-------------------|
| Mixed-unit test didn’t inspect rows | Added row-level `source_timestamp_unit` + normalized open assertions |
| CoverageWindow not asserted | Added invalid-time exclusion + valid inclusion bounds tests |
| Calendar tests only parser-level | Added `1M` Jan31→Feb28 month-end normalization + leap-year 2020-02-29 bar |
| Market tests only names | Added USD-M + COIN-M column sets and partition `volume_unit`/`secondary_volume_unit` |
| `verify_outputs` only, not `publish` | Added temp catalog/store publication regression; surfaces empty `config_sha256` source defect |
| Hard-coded network-test path | Replaced with `importlib.resources` lookup for portability |
| Change-report claims exceeded tests | Reports exact counts/commands/hash only |

### Production defect exposed by publication regression

`DatasetPublisher.publish(plan)` currently fails at existing-manifest validation:

```
CorruptDatasetError: manifest schema validation failed:
config_sha256 String should match pattern '^[a-f0-9]{64}$'
```

Source cause: `binance.py` builds `PublishPlan` with `ConfigIdentity(config_sha256="")`.
Ref: `src/cryptofactors/ingest/binance.py` — `ConfigIdentity(config_sha256=...)` constants blocked here per review policy; routing required.

## Fresh validation commands and results

Run from repo root at integration commit `727ca56`.
| Command | Result |
|---------|--------|
| `PYTHONPATH=src uv run pytest tests/ingest/market -q --tb=short` | 25 passed |
| `PYTHONPATH=src uv run ruff check src/cryptofactors/ingest tests/ingest/market` | All checks passed |
| `PYTHONPATH=src uv run mypy --no-incremental src/cryptofactors/ingest tests/ingest/market` | Success |
| `PYTHONPATH=src uv run pytest -q` | passed |
| `python3 scripts/check_repo_control.py` | PASS |

## Git artifacts

Pending record:

- Integration commit: `727ca56ed1d247eb409613e9e5e0aaac6eae3d41` (origin/main)
