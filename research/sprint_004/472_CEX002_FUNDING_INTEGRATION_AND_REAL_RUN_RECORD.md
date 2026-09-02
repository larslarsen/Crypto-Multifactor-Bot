# Record 472 — Funding Integration and Real Run

**Ticket:** CEX-002
**Actor:** Jr Dev — Hermes
**Start UTC:** 2026-09-02T23:06:19Z
**End UTC:** 2026-09-02T23:13:05Z
**Exit code:** 0

## Preproof

```
HEAD == origin/main == 1a5b646df19434b006e8f511e2067480bc0bc8a6
Source SHA-256 4e38658f89905e1f5b66b739eb8f58e2f66ce204b9c61cfbfa7cb0ed161acada 1,404 lines
CLI SHA-256    05e30c8712608e4895749114375a9b38ea5cf868870d913ddef5d264f77d7b2b 50 lines
Test SHA-256   b7b9add7396ff8a3bac4717ae60a7048f7282b0a0117b27c14bfe55d978a0183 907 lines
```

Ordered checks (all passed):
1. `pytest tests/ingest/test_binance_usdm_funding_realized.py -q --tb=short` → exit 0, 66/66 cases
2. `ruff check <three paths>` → exit 0, All checks passed!
3. `check_repo_control.py` → exit 0, PASS

## Integration

Staged and committed exactly the three accepted paths:
```
e8a4443 CEX-002: integrate realized funding normalizer
3 files changed, 2361 insertions(+)
```
Pushed. `HEAD == origin/main == e8a4443852606786d3f14ab533bbf671786c4c5e`

## Real run preproof

- Output root `data/.cex002_funding_realized` absent and not a symlink
- No running funding normalizer (ps clean)
- Available bytes pre: 556,026,527,744 (above 110,648,021,942 floor)

## Command (executed exactly once, foreground, attached)

```bash
PYTHONPATH=src .venv/bin/python scripts/research/normalize_binance_usdm_funding_realized.py \
  --generation0-state data/cex002_qualify/gate2/state.sqlite \
  --generation0-content-root data/cex002_qualify/gate2/content \
  --report research/sprint_004/62_CEX002_GATE1_SOURCE_PROCUREMENT.json \
  --sizing research/sprint_004/258_CEX002_GATE2_STORAGE_SIZING_V3.json \
  --output-root data/.cex002_funding_realized
```

## Terminal outcome

Exit code: 0
Wall time: ~6m46s (start 23:06:19Z, end 23:13:05Z)
Process absent at observation.
Available bytes post: 555,347,001,344

Exact stdout:
```json
{"collapsed_identical_rows":0,"completion_sha256":"57628164f19d182164b6058d9e51f794430cc918706c088f430e1c01d2898522","partition_count":21035,"physical_source_rows":2683024,"product_rows":2683024,"schema_sha256":"02c7ba85ad5a8fc701d97f2b9fffc307c2aa88e4374772c6c1156e55fc7b5202"}
```

## Descriptor

- Completion path: `data/.cex002_funding_realized/.complete/57628164f19d182164b6058d9e51f794430cc918706c088f430e1c01d2898522.json`
- Completion SHA-256: `57628164f19d182164b6058d9e51f794430cc918706c088f430e1c01d2898522` (matches file content)
- Normalizer source SHA-256: `4e38658f89905e1f5b66b739eb8f58e2f66ce204b9c61cfbfa7cb0ed161acada`
- Schema SHA-256: `02c7ba85ad5a8fc701d97f2b9fffc307c2aa88e4374772c6c1156e55fc7b5202` (= `product_schema_identity("binance_usdm_funding_realized")`)

### Source authority

| Metric | Value |
|---|---|
| selected_sources | 21,035 |
| selected_source_bytes | 21,351,804 |
| checksum_verified_sources | 21,020 |
| retained_credit_sources | 15 |
| binance_completions | 685,072 |
| seal_head_receipt_sha256 | `8875338d0a2b7984fb8fefd7a716a04486667cfb1d726c3758f5496f065ef7ab` |
| sources_sha256 | `3c8bd792b046249f31d8ad7966c96d677b7926eecf3b7db2b84e173829e57108` |
| report_sha256 | `f27b2ba7e6eff3a8b1385d985c49ee64ef60a394737b1246130d0f37b9015f09` |
| sizing_sha256 | `3995a5072a7d84baecae677ceff6e1c7af9dd076daadec04a31717ffc8f16589` |

### Row equation

| Metric | Value |
|---|---|
| physical_source_rows | 2,683,024 |
| collapsed_identical_rows | 0 |
| conflicting_events | 0 |
| rounded_events | 0 |
| inferred_events | 0 |
| excluded_source_rows | 0 |
| product_rows | 2,683,024 |

Equation: 2,683,024 − 0 = 2,683,024 ✓ (zero-collapse, zero-exclusion event product)

### Observed event-time range

| Metric | Value |
|---|---|
| calc_time_min | 1577836800000 (2020-01-01T00:00:00Z) |
| calc_time_max | 1785538800000 (2026-07-31T03:00:00Z) |
| native_symbol_min | `0GUSDT` |
| native_symbol_max | `ZRXUSDT` |

### Interval histogram

| funding_interval_hours | event_count |
|---|---|
| 1 | 78,745 |
| 2 | 3,639 |
| 4 | 1,468,646 |
| 8 | 1,131,994 |
| **total** | **2,683,024** ✓ |

Interval range: min 1h, max 8h.

### Partition/lineage inventory

- partitions/ Parquet files: 21,035
- lineage/ JSON files: 21,035
- total_parquet_bytes: 134,139,692
- total_lineage_bytes: 27,750,608
- sole completion file (exactly one)
- staging directory empty (0 files)
- extra unreferenced files: 0

## Independent descriptor-referenced reconciliation

Every descriptor-referenced partition Parquet, lineage document, and the single completion file was read back from disk and checked:

- Parquet hash matches: 21,035 / 21,035 (0 failures)
- Lineage hash matches: 21,035 / 21,035 (0 failures)
- Parquet schema matches the normalizer's `SCHEMA` constant (verified via PyArrow equality + `product_schema_identity` on one file, then the normalizer's publish-time `schema_arrow == SCHEMA` check on every partition)
- Summed row count across all Parquet metadata: 2,683,024 = product_rows ✓
- Every Parquet is a regular file (not symlink, not missing)
- Every lineage is a regular file (not symlink, not missing)
- Every path is beneath `data/.cex002_funding_realized`

The `schema_sha256` in the descriptor is `product_schema_identity(PRODUCT)` (the canonical SHA-256 of `{required_product, schema_contract}`, per `src/cryptofactors/acquisition/binance_usdm_harmonic_sizing.py:2083`), NOT a raw Arrow serialization. The normalizer's per-partition publish-time check `parquet.schema_arrow == SCHEMA` (line 854 of the source) confirms every on-disk schema equals the frozen domain schema. A spot-check on `.partitions/0GUSDT/2025-09/e59f4f37...parquet` confirmed `schema_arrow == SCHEMA → True`, 233 rows, 1 row group.

## Capacity

| Metric | Value |
|---|---|
| Pre-run avail | 556,026,527,744 |
| Post-run avail | 555,347,001,344 |
| Floor | 110,648,021,942 |
| Above floor | ✓ |

## Process and process tree

No `binance_usdm_funding_realized` / `normalize_binance_usdm_funding` process found at observation (ps aux clean).

## Publication

- Record 472 published.
- `docs/handoff/CURRENT_TASK.md` updated.
- `tickets/CEX-002.md` updated.
- Both actor fields returned to the Lead Quantitative Finance Researcher/Engineer.
- Gate 3 and CEX-002 remain `IN_PROGRESS`. Next ticket remains `NONE`.

No retry, wrapper, detach, source/test patch, deletion, cleanup, other product, coverage product, bundle, catalog transaction, NautilusTrader check, experiment, model, Harmonic Trader work, PAPER, LIVE, or next-ticket work was authorized or performed. Temporary reconciliation scripts removed.
