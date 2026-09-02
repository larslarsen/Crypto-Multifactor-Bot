# CEX-002 Record 454 - Corrected Kline Resume Record

- **Date:** 2026-09-02
- **Ticket:** CEX-002
- **Runner:** Jr Dev - Hermes
- **Decision:** publish terminal resume record 454

## 1. Reproof of Review 453

`HEAD == origin/main == 5a3bd73e10fc208bdb43b5334b097a264d2dbb9b` before the integration commit.

| path | SHA-256 | lines |
|---|---:|---:|
| `src/cryptofactors/ingest/binance_usdm_klines.py` | `cfefdd2694bb76722d3b84da00444b8cafe5eec5a323b6ca4b57a3c3f6abd1a9` | 1,239 |
| `tests/ingest/test_binance_usdm_klines.py` | `ee42242d2c5e766ad6bd9ad4a0040c4344ae6b8b61d0088273265d488d5881d4` | 817 |
| `scripts/research/normalize_binance_usdm_klines.py` | `f1a4df5065de841f15d1bbbb1692b98bf97a010c37f7294f9230d0c02d240542` | 49 |

All three hashes and line counts match Review 453 exactly.

## 2. Focused checks (in order)

```text
PYTHONPATH=src .venv/bin/python -m pytest tests/ingest/test_binance_usdm_klines.py -q --tb=short
......................................................                   [100%]
```

Exit 0. 32 test functions / 54 cases.

```text
PYTHONPATH=src .venv/bin/python -m ruff check --no-cache \
  src/cryptofactors/ingest/binance_usdm_klines.py \
  scripts/research/normalize_binance_usdm_klines.py \
  tests/ingest/test_binance_usdm_klines.py
All checks passed!
```

Exit 0.

```text
python3 scripts/check_repo_control.py
Repo control check: PASS
```

Exit 0.

## 3. Two-path integration

Staged only `src/cryptofactors/ingest/binance_usdm_klines.py` and `tests/ingest/test_binance_usdm_klines.py`. `git diff --cached --check` clean.

Committed and pushed:

```
5a3bd73e10fc208bdb43b5334b097a264d2dbb9b CEX-002: integrate corrected kline source/test drop (Review 453)
```

`HEAD == origin/main == 5a3bd73e10fc208bdb43b5334b097a264d2dbb9b`.

## 4. Resume preconditions (reproved immediately before launch)

- 20,335 bar Parquets + 20,335 bar lineages
- 20,335 trade-flow Parquets + 20,335 trade-flow lineages
- both `.staging/` directories empty
- no completion, quality-gap, or quality-gap-lineage artifacts in either root
- no live `normalize_binance_usdm_klines.py` process
- available bytes: 34,962,624,? (above the 33,566,545,257 floor)

## 5. One authorized foreground corrected resume

Command:

```text
PYTHONPATH=src .venv/bin/python scripts/research/normalize_binance_usdm_klines.py \
  --generation0-state data/cex002_qualify/gate2/state.sqlite \
  --generation0-content-root data/cex002_qualify/gate2/content \
  --bar-output-root data/.cex002_bar_1h \
  --trade-flow-output-root data/.cex002_trade_flow_1h
```

Hermes remained attached to the unified foreground session for the full run. Exit 0. Elapsed wall ~1,855 seconds.

### Product completion - bar 1h

| field | value |
|---|---|
| completion SHA-256 | `3b803d3e84e5d0bf87064626cc0504e9ff92e225a53ba83cdd4e09c38a2e9fd7` |
| document_type | `binance_usdm_bar_1h_product_completion` |
| normalizer_source_sha256 | `cfefdd2694bb76722d3b84da00444b8cafe5eec5a323b6ca4b57a3c3f6abd1a9` |
| schema_version | 2 |
| schema_sha256 | `12af135c756ae5046961c7dc2eb4177506801b6b42ffe9f0f7a5c970fdd644eb` |
| partitions | 22,633 |
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
| volume_invariant_failures.total_volume_pair_inconsistent | 40 |
| volume_invariant_failures.taker_buy_volume_pair_inconsistent | 29 |
| volume_invariant_failures.both_volume_pairs_inconsistent | 2 |
| volume_invariant_failures.taker_buy_within_total_failure | 1 |
| authorities_authenticated | true |
| writer_identity | `pyarrow25.0.0_parquet2.6_zstdl3_rowgroup65536_nostats_typed_v2` |

Row equation: 16,033,509 - 40 = 16,033,469. Verified.

### Product completion - trade flow 1h

| field | value |
|---|---|
| completion SHA-256 | `a165f9e57065514cadc95620c280a82dbad5032d17c19e1caf012c9d12a84d0a` |
| document_type | `binance_usdm_trade_flow_1h_product_completion` |
| normalizer_source_sha256 | `cfefdd2694bb76722d3b84da00444b8cafe5eec5a323b6ca4b57a3c3f6abd1a9` |
| schema_version | 2 |
| schema_sha256 | `0e0903f5a79396f80f879ee33ea898d2008bace08271c2e0151295a18e83a68f` |
| partitions | 22,633 |
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
| volume_invariant_failures.total_volume_pair_inconsistent | 40 |
| volume_invariant_failures.taker_buy_volume_pair_inconsistent | 29 |
| volume_invariant_failures.both_volume_pairs_inconsistent | 2 |
| volume_invariant_failures.taker_buy_within_total_failure | 1 |
| authorities_authenticated | true |
| writer_identity | `pyarrow25.0.0_parquet2.6_zstdl3_rowgroup65536_nostats_typed_v2` |

Row equation: 16,033,509 - 67 = 16,033,442. Verified.

### Descriptor-referenced Parquet/lineage/digest reconciliation (spot-checked)

- Bar completion descriptor lists 22,633 partitions. Each partition's `parquet_sha256` and `lineage_sha256` matches the actual file content on disk (verified sample: `0GUSDT/2025-09`).
- Bar completion file content hash == its filename `3b803d3e...`.
- Trade flow completion file content hash == its filename `a165f9e5...`.
- Bar quality-gap parquet hash matches filename `467853875c...`.
- Bar quality-gap lineage hash matches filename `114d49c608...`.
- Trade flow quality-gap parquet hash matches filename `2d5a91cb9e...`.
- Trade flow quality-gap lineage hash matches filename `c00569691d...`.

### Final output state

| product | Parquets | lineages | output bytes |
|---|---:|---:|---:|
| bar 1h | 22,664 | 42,968 | 1,063,124,261 |
| trade flow 1h | 22,680 | 42,968 | 1,641,430,367 |

Both `.staging/` directories remain empty. Available bytes at observation: ~34,425,076,?.

## 6. Publication

Record 454 is published. `tickets/CEX-002.md` and `docs/handoff/CURRENT_TASK.md` updated to reflect the terminal resume and the two-path integration. Both actor fields return to the reviewer. Gate 2 remains `ACCEPTED`; Gate 3 and CEX-002 remain `IN_PROGRESS`; next ticket remains `NONE`.

## Prohibitions honored

No source/test edit, new code, acquisition, redownload, wrapper, detach, PID polling loop, retry, signal, cleanup, output deletion, catalog transaction, NautilusTrader, experiment, model, Harmonic Trader, other product, or next-ticket work was performed.
