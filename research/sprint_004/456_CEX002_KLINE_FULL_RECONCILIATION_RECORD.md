# CEX-002 Record 456 — Full Kline Reconciliation Record

- **Date:** 2026-09-02
- **Ticket:** CEX-002
- **Runner:** Jr Dev - Hermes
- **Decision:** publish terminal full reconciliation record 456

## 1. Scope

This record publishes the exact results of the one read-only full audit authorized by
Review 455. It verifies both accepted completion descriptors and every one of their
22,633 referenced partition Parquets and lineage documents per product, plus the
quality-gap artifacts and exclusion-set reconciliation. It distinguishes descriptor-
referenced files from older unreferenced content-addressed files.

No normalizer or test was run. No source, test, CLI, or data was edited. Nothing was
downloaded. No network was used. `run_continuation_runner.sh` was not read or invoked.

## 2. Audit method

A single deterministic Python script (`scripts/research/audit_cex002_record456.py`) was
authored and executed once under `.venv/bin/python`. It performed these steps in order:

1. Verified each completion file is the sole entry in `.complete/`, is a regular
   non-symlink file, and its SHA-256 equals both its filename and the accepted
   completion identity.
2. Verified each descriptor has exactly 22,633 unique `(native_symbol, utc_month)`
   partition entries, unique canonical relative Parquet and lineage paths, the accepted
   product/schema/normalizer/source identities, and the exact accepted row, invariant,
   exclusion, and gap totals.
3. For all 22,633 entries per product, verified both referenced files are regular
   non-symlink files beneath the held product root; each complete file SHA-256 equals
   the descriptor value and its content-addressed filename; each Parquet metadata row
   count equals the descriptor row count; and each lineage document hash and
   product/symbol/month/row/schema/Parquet binding agrees with its descriptor entry.
4. Verified aggregate descriptor and Parquet metadata row counts equal 16,033,469 for
   bars and 16,033,442 for trade flow.
5. Verified the referenced quality-gap Parquet and lineage files have exact hashes,
   schemas, row counts, and missing-grid totals; the lineage's canonical exclusion hash
   recomputes (using `_canonical_json` = `json.dumps(..., sort_keys=True, separators=(",", ":"), ensure_ascii=True) + "\n"`); and every provider-invalid gap has exactly
   one matching exclusion lineage entry.
6. Verified the bar exclusion set has 40 unique raw-row identities, the trade-flow set
   has 67, the bar set is a subset of trade flow, and the trade-flow-only set has 27.
7. Verified staging is empty, no normalizer is running, current exact available bytes
   are recorded as a new audit-time observation, and physical artifact inventories
   explicitly separate descriptor-referenced files from old unreferenced
   content-addressed files.

The audit stops on the first mismatch and records it without repair. Zero mismatches
were found.

## 3. Completion file verification

| field | bar 1h | trade flow 1h |
|---|---|---|
| sole file in `.complete/` | yes | yes |
| regular non-symlink file | yes | yes |
| SHA-256 matches filename | yes | yes |
| SHA-256 matches accepted identity | yes | yes |

Bar completion SHA-256: `3b803d3e84e5d0bf87064626cc0504e9ff92e225a53ba83cdd4e09c38a2e9fd7`
Trade-flow completion SHA-256: `a165f9e57065514cadc95620c280a82dbad5032d17c19e1caf012c9d12a84d0a`

## 4. Descriptor verification

### Bar 1h

| field | value |
|---|---|
| document_type | `binance_usdm_bar_1h_product_completion` |
| normalizer_source_sha256 | `cfefdd2694bb76722d3b84da00444b8cafe5eec5a323b6ca4b57a3c3f6abd1a9` |
| schema_version | 2 |
| schema_sha256 | `12af135c756ae5046961c7dc2eb4177506801b6b42ffe9f0f7a5c970fdd644eb` |
| partitions | 22,633 |
| unique (native_symbol, utc_month) | 22,633 |
| unique parquet paths | 22,633 |
| unique lineage paths | 22,633 |
| source_count | 35,642 |
| source_bytes | 661,676,054 |
| sources_sha256 | `5d414eb6a1715b483afa532e092a55955c98132c1e106117850cb763ee4c5c8f` |
| physical_rows | 16,033,509 |
| product_rows | 16,033,469 |
| excluded_rows | 40 |
| quality_gap_row_count | 154 |
| quality_gap_parquet_sha256 | `467853875cfb1570dcb6de953f4af54af03cab4adf6c9fd7a39143a83c4cc9e4` |
| quality_gap_lineage_sha256 | `114d49c6082be8ae0fd902b3a0e7642a0b3d0e553a951cc32b780a69544c0832` |
| missing_grid_points | 8,043 |
| aggregate parquet metadata rows | 16,033,469 |
| aggregate descriptor row_count | 16,033,469 |
| volume_invariant_failures.total_volume_pair_inconsistent | 40 |
| volume_invariant_failures.taker_buy_volume_pair_inconsistent | 29 |
| volume_invariant_failures.both_volume_pairs_inconsistent | 2 |
| volume_invariant_failures.taker_buy_within_total_failure | 1 |
| authorities_authenticated | true |
| writer_identity | `pyarrow25.0.0_parquet2.6_zstdl3_rowgroup65536_nostats_typed_v2` |

Row equation: 16,033,509 - 40 = 16,033,469. Verified.

### Trade flow 1h

| field | value |
|---|---|
| document_type | `binance_usdm_trade_flow_1h_product_completion` |
| normalizer_source_sha256 | `cfefdd2694bb76722d3b84da00444b8cafe5eec5a323b6ca4b57a3c3f6abd1a9` |
| schema_version | 2 |
| schema_sha256 | `0e0903f5a79396f80f879ee33ea898d2008bace08271c2e0151295a18e83a68f` |
| partitions | 22,633 |
| unique (native_symbol, utc_month) | 22,633 |
| unique parquet paths | 22,633 |
| unique lineage paths | 22,633 |
| source_count | 35,642 |
| source_bytes | 661,676,054 |
| sources_sha256 | `5d414eb6a1715b483afa532e092a55955c98132c1e106117850cb763ee4c5c8f` |
| physical_rows | 16,033,509 |
| product_rows | 16,033,442 |
| excluded_rows | 67 |
| quality_gap_row_count | 181 |
| quality_gap_parquet_sha256 | `2d5a91cb9e146e4adc2a65e1868fe8cf85682978847649f506de5b6f602cef6b` |
| quality_gap_lineage_sha256 | `c00569691dee41f220e7a5abe2a3b0446ea8c3c5d93febf4802b315ee8e24f46` |
| missing_grid_points | 8,070 |
| aggregate parquet metadata rows | 16,033,442 |
| aggregate descriptor row_count | 16,033,442 |
| volume_invariant_failures.total_volume_pair_inconsistent | 40 |
| volume_invariant_failures.taker_buy_volume_pair_inconsistent | 29 |
| volume_invariant_failures.both_volume_pairs_inconsistent | 2 |
| volume_invariant_failures.taker_buy_within_total_failure | 1 |
| authorities_authenticated | true |
| writer_identity | `pyarrow25.0.0_parquet2.6_zstdl3_rowgroup65536_nostats_typed_v2` |

Row equation: 16,033,509 - 67 = 16,033,442. Verified.

## 5. Full partition audit (22,633 per product)

All 22,633 bar partitions and all 22,633 trade-flow partitions were verified:

- Every referenced Parquet exists as a regular non-symlink file beneath the product root.
- Every Parquet SHA-256 equals the descriptor value and its content-addressed filename.
- Every Parquet metadata row count equals the descriptor `row_count`.
- Every lineage document exists as a regular non-symlink file beneath the product root.
- Every lineage SHA-256 equals the descriptor value and its content-addressed filename.
- Every lineage `document_type`, `required_product`, `native_symbol`, `utc_month`,
  `row_count`, `parquet_sha256`, `schema_sha256`, `writer_identity`, `schema_version`,
  and `parquet_name` agrees with the descriptor entry and accepted identities.

Schema identity recomputed from the accepted sizing module matches the descriptor:
- Bar schema identity: `12af135c756ae5046961c7dc2eb4177506801b6b42ffe9f0f7a5c970fdd644eb` (matches)
- Trade-flow schema identity: `0e0903f5a79396f80f879ee33ea898d2008bace08271c2e0151295a18e83a68f` (matches)

## 6. Quality-gap artifact verification

| field | bar 1h | trade flow 1h |
|---|---|---|
| quality-gap parquet exists | yes | yes |
| quality-gap parquet SHA-256 matches filename | yes | yes |
| quality-gap parquet row count matches descriptor | yes (154) | yes (181) |
| quality-gap lineage exists | yes | yes |
| quality-gap lineage SHA-256 matches filename | yes | yes |
| lineage document_type matches | yes | yes |
| lineage required_product matches | yes | yes |
| lineage row_count matches | yes (154) | yes (181) |
| lineage missing_grid_points matches | yes (8,043) | yes (8,070) |
| lineage provider_invalid_exclusion_count matches | yes (40) | yes (67) |
| canonical exclusion hash recomputes | yes | yes |

## 7. Exclusion-set reconciliation

| metric | value |
|---|---|
| bar unique raw-row identities | 40 |
| trade-flow unique raw-row identities | 67 |
| bar subset of trade-flow (ignoring reason/flags) | yes |
| trade-flow-only identities | 27 |

Raw-row identity = `(native_symbol, utc_month, open_time, source_key, source_row_ordinal)`.
The `reason` and `failed_invariant_flags` fields differ between products (bar uses
`provider_inconsistent_total_volume_pair`; trade-flow uses
`provider_inconsistent_trade_flow_required_volume`), so they are excluded from the
subset comparison. The underlying corrupted rows are identical.

## 8. Staging, process, and capacity

| check | result |
|---|---|
| bar `.staging/` empty | yes |
| trade-flow `.staging/` empty | yes |
| live `normalize_binance_usdm_klines.py` process | none |
| available bytes at audit time | 24,704,761,856 (new observation) |

## 9. Physical artifact inventory (referenced vs. unreferenced)

### Bar 1h root

| category | physical | referenced | unreferenced |
|---|---:|---:|---:|
| `.partitions/*.parquet` | 22,664 | 22,633 | 31 |
| `.lineage/*.json` | 42,968 | 22,633 | 20,335 |
| `.quality-gaps/*.parquet` | 1 | 1 | 0 |
| `.quality-gap-lineage/*.json` | 1 | 1 | 0 |
| `.complete/*.json` | 1 | 1 | 0 |

### Trade flow 1h root

| category | physical | referenced | unreferenced |
|---|---:|---:|---:|
| `.partitions/*.parquet` | 22,680 | 22,633 | 47 |
| `.lineage/*.json` | 42,968 | 22,633 | 20,335 |
| `.quality-gaps/*.parquet` | 1 | 1 | 0 |
| `.quality-gap-lineage/*.json` | 1 | 1 | 0 |
| `.complete/*.json` | 1 | 1 | 0 |

The 20,335 unreferenced lineage files in both roots are pre-existing content-addressed
artifacts from earlier partial runs (before the corrected kline resume). They are not
referenced by either completion descriptor. The 31 / 47 unreferenced Parquets are
similarly older content-addressed artifacts. All unreferenced files are preserved
untouched as content-addressed evidence.

## 10. Audit result

PASS. All 22,633 partitions per product, all quality-gap artifacts, and all exclusion
sets were verified exactly. Zero mismatches. The two completed products are fully
reconciled against their completion descriptors.

## 11. Prohibitions honored

No source/test edit, new code beyond the read-only audit script, acquisition, redownload,
wrapper, detach, PID polling loop, retry, signal, cleanup, output deletion, catalog
transaction, NautilusTrader, experiment, model, Harmonic Trader, other product, or
next-ticket work was performed. The audit script is a read-only artifact and is not
part of the committed deliverable.

## 12. Publication

Record 456 is published. `tickets/CEX-002.md` and `docs/handoff/CURRENT_TASK.md` updated
to reflect the full reconciliation. Both actor fields return to the reviewer. Gate 2
remains `ACCEPTED`; Gate 3 and CEX-002 remain `IN_PROGRESS`; next ticket remains `NONE`.
