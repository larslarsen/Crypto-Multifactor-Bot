# 12 — AUD-003 Source-Feasibility Audit Execution

**Ticket:** AUD-003
**Toolkit:** accepted `source_audit` (AUD-002, commit `899fb7c802dc4ba9b951118598417aef6d22cdcb`)
**Runner:** `scripts/audit/run_sprint003_audit.py`
**Staging (external, not committed):** `/tmp/crypto_source_audit/`
**Outputs:** `research/sprint_003/audit_results/` (deterministic JSON + CSV)

## Commands executed

```
PYTHONPATH=src uv run python scripts/audit/run_sprint003_audit.py \
    --staging /tmp/crypto_source_audit \
    --out research/sprint_003/audit_results
```

The runner loads the 43-record `evidence_manifest.csv`, reconciles each staged
object (SHA-256 + byte-size cross-check), then runs the toolkit:

- `source_audit.compute_sha256` — immutable-object SHA-256 verification
- `source_audit.audit_zip_safe` — bounded ZIP inspection (no extraction)
- `source_audit.infer_timestamp_unit` — timestamp-unit inference (header-auto-detected sampling)
- `source_audit.compare_binance_archive_precision` — adjacent-archive precision comparison
- `source_audit.compute_storage_stats` — bytes/row stats + U25/U50/U100 projections

## Configurations used (per audit)

- **SHA-256:** SHA-256 over full file bytes; content-addressed.
- **ZIP safety:** max_members=1000, max_ratio=100.0, max_total_extracted=2 GiB.
- **CSV/timestamp:** per-archive header auto-detect; timestamp column per schema
  (spot/perp aggTrades ts=5, perp trades ts=4, klines ts=0, funding ts=0);
  UTC bounds 2017-01-01 .. 2027-01-01; sample_rows=20; encoding=utf-8; delimiter=",".
- **Binance precision compare:** member_suffix=.csv, timestamp_column=5,
  has_header=False, min_valid_inferences=5, max_malformed_rate=0.1,
  max_ambiguous_rate=0.05 (per toolkit contract).
- **Storage stats:** basis=extracted, upper_quantile=0.9, stress_case_bytes_per_row=200,
  ProjectionAssumptions: U25=25, U50=50, U100=100, rows_per_asset_per_period=1,000,000,
  retention_periods=365, replication_factor=1, overhead_multiplier=1.2,
  safety_multiplier=1.5.

## Staged input locations (no machine-specific secrets embedded)

- `binance/` — 6 ZIP archives (aggTrades daily 2024-12-31 & 2025-01-01, perp aggTrades
  2025-01-01, perp trades 2025-01-01, klines 1m 2025-01-01, funding monthly 2025-01) +
  4 `.CHECKSUM` sidecars + replacement-checksum register + README.
- `bybit/` — 2 `.csv.gz` archives (BTCUSD 2019-10-01, BTCUSDT 2020-03-25) + instrument/
  funding JSON snapshots.
- `coin_metrics/` — catalog + timeseries JSON, error responses, headers, docs.
- `defillama/`, `okx/`, `kraken/`, `token_unlocks/` — docs, adapter files, live samples.

## Outputs produced

`evidence_reconciliation.json` + `.csv`, `hash_verification.json`,
`archive_safety.json`, `csv_schema_timestamp.json`, `binance_precision_comparison.json`,
`pagination.json`, `bar_reconstruction_comparison.json`, `storage_statistics.json`,
`execution_manifest.json`. All JSON is deterministic (verified: identical byte hashes
across two independent runs).

## Reconciliation result (43 records)

- **present:** 40 — hash-verifiable, byte-size matches manifest.
- **duplicated:** 1 — EV-015 identical content to EV-013 (both Kraken HTML snapshots).
- **missing:** 1 — EV-041 (`token_unlocks/tokenomist_arb.json`) declared but absent on disk.
- **inaccessible:** 1 — EV-019 (OKX) no local_path in manifest.
- **corrupt:** 0, **superseded:** 0.

## Key audit findings (factual, not conclusions)

- All 6 Binance ZIP archives pass `audit_zip_safe` (bounded; compression ratios 3.2–6.4,
  no zip-bomb signature).
- Timestamp-unit inference (via `infer_timestamp_unit`):
  - spot aggTrades 2024-12-31 → **millisecond**
  - spot aggTrades 2025-01-01 → **microsecond** (unit change within the archive pair)
  - perp aggTrades 2025-01-01 (sample) → ms; perp trades 2025-01-01 → ms
  - klines 1m 2025-01-01 → **microsecond**; funding 2025-01 → ms
  - 0 malformed across all 120 sampled rows.
- `compare_binance_archive_precision` **failed**: the toolkit rejects headerless
  archives (`has_header=True` required). The daily Binance aggTrades dumps are
  headerless, so the designed adjacent-archive precision comparison cannot run on the
  real daily dumps as-is. (Surfaced as a failed record, not omitted.)
- Storage statistics (6 samples, extracted basis): median 74.96 bytes/row; U100
  projection ≈ 7.92e12 bytes under base assumptions; stress case (200 B/row) ≈ 1.31e13.

## Missing evidence / failed or inconclusive checks

- EV-041 Tokenomist ARB JSON missing from staging (TLS-unreachable at collection time).
- EV-019 OKX has no staged artifact (DNS-unreachable bulk host).
- Binance precision comparison inconclusive (toolkit headerless limitation — see above).
- Pagination not executed: Bybit cursor pages are static snapshots, not a replayable
  fetch sequence; no synthetic pagination run performed (no fabrication).
- Bar reconstruction/comparison not executed: requires overlapping trade+candle samples
  over a shared interval; deferred. No synthetic bars produced (no fabrication).

## Limitations

- Audits cover the 43 collected manifest records only; no live re-fetch.
- Storage projections use explicit caller-supplied universe counts (no research-derived
  base universe).
- Comparison tolerances and bar alignment were not exercised (no overlapping sample set).

---

## Evidence awaiting Research Lead interpretation

The following are factual audit outputs that require Research Lead judgment. They are
**not** source-acceptance or rejection decisions, and no research hypotheses were
revised by this audit.

1. **Binance aggTrades timestamp unit transition (ms → us):** spot aggTrades 2024-12-31
   infers millisecond timestamps while 2025-01-01 infers microsecond. The toolkit's
   `infer_timestamp_unit` flags this cleanly; whether the production pipeline must
   handle both units (and the precision-vs-accuracy implication) is a Research Lead
   decision.

2. **`compare_binance_archive_precision` cannot run on headerless daily dumps:**
   the toolkit hard-requires `has_header=True`, but Binance daily aggTrades/klines are
   headerless. This blocks the designed adjacent-archive precision transition check on
   real data. Possible resolutions: (a) add headerless support to the toolkit, or
   (b) run precision comparison on the *headed sample* archives (which are ms, not the
   transition pair). Flagged as a potential toolkit defect for escalation.

3. **Duplicate Kraken evidence (EV-015 == EV-013):** two manifest rows reference
   identical HTML; one may be redundant. No content defect, but the manifest double-counts.

4. **Kraken fetch entirely failed at collection (DNS 404):** no Kraken bulk files are
   available for audit; Kraken feasibility cannot be assessed from this evidence.

5. **Missing/inaccessible providers:** Tokenomist (EV-041 missing), OKX (EV-019 no
   artifact), DefiLlama emissions (HTTP 402 paid), Messari (account-gated). These
   sources are not represented in auditable evidence and remain open gaps.

6. **Storage projection assumptions are placeholder:** U25/U50/U100 universe sizes
   (25/50/100) and 1e6 rows/asset/period are illustrative, not research-derived. The
   projection math is validated; the inputs are not a feasibility conclusion.
