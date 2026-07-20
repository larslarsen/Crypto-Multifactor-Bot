# BAR-001 — Sr source drop (canonical bar publisher)

**Status:** Ready for Jr integration and test coverage  
**Production package (already in tree):**  
- `src/cryptofactors/market/__init__.py`  
- `src/cryptofactors/market/bars.py`  
**Transform:** `canonical_bar_publisher` version `1`  
**Schema:** `market_bar` version `1` (UTC-µs physical timestamps)  
**Governing:** `tickets/BAR-001.md`, `docs/handoff/CURRENT_TASK.md`,  
`docs/architecture/01_DATA_ARCHITECTURE.md`, REVIEW-0025 (BIN-001 accepted)  
**Migration:** none  

Sr Dev — Grok Build source-only drop. No tests, Git, commits, pushes, or
acceptance runs by Sr. Jr Dev — Hermes owns everything below.

## What was implemented

Public API: `cryptofactors.market.publish_canonical_bars`

### Inputs
- `SourceBarDatasetRef` — immutable **local** source-normalized bar Parquet paths
  (BIN-001-style) with explicit `dataset_id`, `quality_status`, `venue_id`,
  integer `instrument_id`, `market_type`, `interval`, `schema_variant`.
- Optional `DailySourceInput` — local source-native daily bars for reconciliation.
- Required `code_commit` (non-empty, not `"unknown"`).
- Optional `config_sha256` (64-hex) or deterministic derivation.
- Explicit `price_tolerance` / `volume_tolerance` (Decimal, default 0).

### Fail-closed quality gate
- Only `PASS` and `PASS_WITH_WARNINGS` source datasets may be promoted.
- `REJECTED` / `QUARANTINED` sources raise `ValueError` (never silently promoted).
- Aligns with REVIEW-0025: rejected BIN-001 partitions are not canonical input.

### Canonical intraday bars
- Map source OHLC + volumes → `market_bar` field names.
- Timestamps: `period_start` / `period_end` / `availability_time` as **int64 UTC µs**.
- Exclusive `period_end = open_time + interval`; `availability_time = period_end`.
- Spot/USD-M: `volume`→`base_volume`, `quote_volume`→`quote_volume`.
- COIN-M: `base_asset_volume`→`base_volume`; no false quote label (0 + flag).
- Stable sort by `(instrument_id, venue_id, timeframe, period_start)`.
- Uniqueness on that key; duplicates → quarantine + `bar001_duplicate_period_start`.

### Daily bars
- Deterministic UTC-day OHLCV resample from accepted intraday (no zero-fill gaps).
- `timeframe=1d`, period = calendar day UTC.

### Reconciliation + quarantine
- Optional native daily compare with explicit Decimal tolerances.
- Mismatches → quarantine rows + `bar001_daily_reconcile_mismatch`.
- Missing native/resampled counterparts → typed issues + report rows.
- Tolerance report parquet always written (may be empty).

### Partitioning + sizing
- Paths: `market_bars/{intraday|daily|quarantine}/venue_id=…/market_type=…/timeframe=…/year=…/month=…/bars.parquet`
- Measured `PartitionSizeMeasurement` (rows + on-disk bytes) per partition.
- Quality issues parquet + MAN-001 `PublishPlan` with `REQUIRE_VERIFIER` row counters,
  dataset dependencies, schema fingerprint, non-empty config hash.

### No network
- Reads only local paths supplied by the caller.

## Jr work

1. Confirm the `cryptofactors.market` package is present as above.
2. Integrate in-tree; **no independent production source changes**.
3. Add focused tests under `tests/market/` (or ticket-specified path) covering:
   - reject REJECTED source datasets
   - promote PASS / PASS_WITH_WARNINGS only
   - exclusive period_end / availability_time from 1m source
   - stable sort + uniqueness → quarantine on duplicate period_start
   - daily resample OHLC/volume correctness across UTC midnight
   - native daily reconcile: match, price/volume mismatch → quarantine, missing sides
   - COIN-M volume mapping (no mislabeled quote)
   - partition path layout year/month + partition size bytes > 0 for non-empty
   - MAN-001: `verify_outputs` and successful `DatasetPublisher.publish` with
     valid `code_commit` and config identity
   - lineage: `source_dataset_id` on every bar; dependency refs on plan
4. Add acceptance commands to `tickets/BAR-001.md` if still absent; run them all
   plus `python3 scripts/check_repo_control.py`.
5. Write `docs/reviews/BAR-001_CHANGE_REPORT.md` with real commands, counts, and
   immutable commit hash.
6. Commit and push per Hermes duties.
7. **Stop for reviewer inspection.** `Next ticket authorized: NONE`.

## Out of scope for this drop

- Migrations, architecture edits, ADR changes  
- Network acquisition / live exchange calls  
- Factor, universe, or execution work  
- Sr tests / Git / acceptance execution  
