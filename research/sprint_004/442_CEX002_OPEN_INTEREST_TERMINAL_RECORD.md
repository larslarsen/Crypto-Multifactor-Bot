# CEX-002 Record 442 — Open Interest Success Reconciliation

- **Date:** 2026-09-01
- **Actor:** Jr Dev — Hermes
- **Ticket:** CEX-002
- **Runner:** `/tmp/cex002_oi_437_XAHLxl` (shell PID 1088968, Python PID 1089049)
- **Decision:** success reconciliation — Review-437 completed with a completion descriptor
- **Gate 2:** `ACCEPTED`
- **Gate 3:** `IN_PROGRESS`
- **Next required actor:** Lead Quantitative Finance Researcher/Engineer
- **Next ticket:** `NONE`

## Reconciliation evidence

The sole Review-437 runner reached terminal state with a completion descriptor. Both
shell PID 1088968 and Python PID 1089049 are absent from `/proc`. No normalize
process remains. The runner completed at 2026-09-01 17:48:46Z (~65 minutes runtime).

### Completion descriptor

- Path: `/home/lars/Crypto_Multifactor_Bot/data/.cex002_open_interest_5m/.complete/bb089fc992326c66ddb65cea03dda92e8cd9fcf7cb7f373821f04a16db9168e4.json`
- Descriptor SHA-256 matches file content: `bb089fc992326c66ddb65cea03dda92e8cd9fcf7cb7f373821f04a16db9168e4` ✓
- File size: 9,231,215 bytes
- Written: 2026-09-01 17:48:46 UTC

### Row equation

| Field | Value |
| --- | --- |
| physical_source_rows | 160,226,578 |
| collapsed_identical_source_rows | 75,255 |
| excluded_source_rows | 2,818 |
| product_rows | 160,148,505 |

Equation: 160,226,578 − 75,255 − 2,818 = **160,148,505** ✓

### Output counts

| Artifact | Count | Bytes |
| --- | --- | --- |
| Parquet partitions | 19,744 | 14,748,166,088 |
| Lineage files | 19,744 | 254,598,455 |
| Quality-gap parquet | 1 | 409,321 |
| Quality-gap lineage | 1 | 1,938 |
| Completion descriptor | 1 | 9,231,215 |
| Staging | 0 | 0 |

All 19,744 parquet SHA-256 hashes match the descriptor. All 19,744 lineage SHA-256
hashes match the descriptor. Quality-gap lineage SHA-256 verified.
Quality-gap parquet SHA-256 verified.

### Authority

- `authorities_authenticated`: true
- `normalized_source_count`: 573,785
- `normalizer_source_sha256`: `c0de316be5a328875935feb9da03d49bb50a404b5d624c12813289b85f3e771b`
- `normalized_sources_sha256`: `2911aeaacd8a065c7f6fd1888052b3e7ee20ad43f3888dc43ca159bd5705f459`
- generation_0.binance_completions: 685,072
- generation_0.metrics_completions: 522,865
- generation_0.seal_head_receipt_sha256: `8875338d0a2b7984fb8fefd7a716a04486667cfb1d726c3758f5496f065ef7ab`
- v3_direct_recovery.book_ticker_rows: 354
- v3_direct_recovery.checksum_conflict_rows: 1
- v3_direct_recovery.listed_bytes: 9,207,379,061
- v3_direct_recovery.manifest_compressed_sha256: `4dacaba97c17ad9c4a9724f5db74dfab7ee98760cdb3df6dea46ab37c0684c2d`
- v3_direct_recovery.manifest_rows: 51,275
- v3_direct_recovery.metrics_rows: 50,921
- v3_direct_recovery.usable_metrics_rows: 50,920

### HBAR checksum conflict

The one typed gap is a provider checksum conflict for HBARUSDC 2026-07-09:
- source_key: `data/futures/um/daily/metrics/HBARUSDC/HBARUSDC-metrics-2026-07-09.zip`
- expected_provider_sha256: `060025bb8887f2c0456d3333fb3a70001f3dfa5662132b0f895a7f3d3247bd52`
- observed_sha256: `8d6e3d3efff6e615be11e43c22df3ecda579aeeb45b3da41c88a65662b5e2cc5`
- etag: `d7f563900c0c2c99b7fd066e02d404c4`
- listed_bytes: 9,810
- outcome: PROVIDER_CHECKSUM_CONFLICT_UNAVAILABLE
- continuity_break: true

### Quality gaps

- `quality_gap_rows`: 57,441
- `typed_gap_count`: 1 (the HBAR conflict above)
- Quality-gap parquet row count: 57,441
- Quality-gap parquet schema: venue, native_symbol, canonical_instrument_id,
  canonical_instrument_version_id, reference_identity_state, required_product,
  utc_month, missing_run_start_ms, missing_run_end_ms, expected_grid_count,
  gap_kind, reason

### Schema

- `schema_sha256`: `385fabea9b59aaead2d926e769808bf810c5a4121de52d577f3400d6fa179c83`
- `writer_identity`: `pyarrow25.0.0_parquet2.6_zstdl3_rowgroup65536_nostats_typed_v2`

### Prior-partition preservation

The twelve 0GUSDT month partitions (2025-09 through 2026-08) are present in the
output with row counts consistent with their calendar lengths:

| Month | Rows |
| --- | --- |
| 2025-09 | 3,843 |
| 2025-10 | 8,928 |
| 2025-11 | 8,640 |
| 2025-12 | 8,928 |
| 2026-01 | 8,928 |
| 2026-02 | 8,064 |
| 2026-03 | 8,928 |
| 2026-04 | 8,640 |
| 2026-05 | 8,927 |
| 2026-06 | 8,640 |
| 2026-07 | 8,928 |
| 2026-08 | 5,181 |

### Runner metadata

- Repository: `/home/lars/Crypto_Multifactor_Bot`
- Source commit: `4a65179e6cd0938a86a556eb0c7f755ab3e283be`
- Command: `PYTHONPATH=/home/lars/Crypto_Multifactor_Bot/src /home/lars/Crypto_Multifactor_Bot/.venv/bin/python /home/lars/Crypto_Multifactor_Bot/scripts/research/normalize_binance_usdm_open_interest.py --generation0-state data/cex002_qualify/gate2/state.sqlite --generation0-content-root data/cex002_qualify/gate2/content --v3-manifest data/cex002_qualify/gate2_revision_candidate_v3/manifest/4dacaba97c17ad9c4a9724f5db74dfab7ee98760cdb3df6dea46ab37c0684c2d.json.gz --recovery-root data/cex002_recovery --output-root data/.cex002_open_interest_5m`
- CWD: `/home/lars/Crypto_Multifactor_Bot`
- Start UTC: 2026-09-01T21:26:20Z
- Shell PID: 1088968
- Shell start tick: 10381675
- Python PID: 1089049
- Terminal: completed at 2026-09-01 17:48:46Z

### Actor fields

Both actor fields return to the Lead Quantitative Finance Researcher/Engineer.
Gate 2 remains accepted; CEX-002 and Gate 3 remain `IN_PROGRESS`. No other
product, bundle, catalog transaction, NautilusTrader check, experiment, backtest,
model, trading engine, or next ticket is authorized.
