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
object (SHA-256 + byte-size cross-check), then runs the toolkit plus runner
adapters:

- `source_audit.compute_sha256` — immutable-object SHA-256 verification
- `source_audit.audit_zip_safe` — bounded ZIP inspection (no extraction)
- `source_audit.infer_timestamp_unit` — timestamp-unit inference (header-auto-detected)
- `source_audit.compare_binance_archive_precision` — native adjacent-archive comparison
- `source_audit.paginate` — static Bybit cursor replay over captured pages
- `source_audit.reconstruct_bars` / `compare_bars` / `normalize_trade` — trade-to-bar
- `source_audit.compute_storage_stats` — bytes/row stats + U25/U50/U100 projections

## Configurations used (per audit)

- **SHA-256:** SHA-256 over full file bytes; content-addressed.
- **ZIP safety:** max_members=1000, max_ratio=100.0, max_total_extracted=2 GiB.
- **CSV/timestamp:** per-archive header auto-detect; timestamp column per schema
  (spot/perp aggTrades ts=5, perp trades ts=4, klines ts=0, funding ts=0);
  UTC bounds 2017-01-01 .. 2027-01-01; sample_rows=20; encoding=utf-8; delimiter=",".
- **Binance headerless precision adapter:** runner-level, mirrors native thresholds
  (min_valid_inferences=5, max_malformed_rate=0.1, max_ambiguous_rate=0.05,
  sample_rows=50) using `infer_timestamp_unit`. Explicitly NOT a native comparator run.
- **Bybit pagination replay:** cursor mode, max_pages=10, max_records=100000;
  deterministic offline fetch callback maps initial request + returned cursors to the
  two captured pages; unknown cursor → empty terminal page.
- **Trade-to-bar:** window=first 10 one-minute intervals (streamed, not full archive);
  price_tolerance=0.01, volume_tolerance=0.0001 (Decimal), closure LEFT_CLOSED_RIGHT_OPEN.
- **Bybit gzip inspection:** stdlib `gzip`; max_decompressed_bytes=200 MiB, max_rows=50000;
  schema/width/parse checks; timestamp unit via `infer_timestamp_unit` on integer seconds.
- **Storage stats:** basis=extracted, upper_quantile=0.9, stress_case_bytes_per_row=200,
  ProjectionAssumptions: U25=25, U50=50, U100=100, rows_per_asset_per_period=1,000,000,
  retention_periods=365, replication_factor=1, overhead_multiplier=1.2,
  safety_multiplier=1.5.

## Staged input locations (no machine-specific secrets embedded)

- `binance/` — 6 ZIP archives (aggTrades daily 2024-12-31 & 2025-01-01, perp aggTrades
  2025-01-01, perp trades 2025-01-01, klines 1m 2025-01-01, funding monthly 2025-01) +
  4 `.CHECKSUM` sidecars + replacement-checksum register + README.
- `bybit/` — 2 `.csv.gz` archives (BTCUSD 2019-10-01, BTCUSDT 2020-03-25) + instrument/
  funding JSON snapshots (`inst_p1.json`, `inst_p2.json`, `fund_p1.json`, etc.).
- `coin_metrics/` — catalog + timeseries JSON, error responses, headers, docs.
- `defillama/`, `okx/`, `kraken/`, `token_unlocks/` — docs, adapter files, live samples.

## Outputs produced (12 reports, deterministic JSON + 1 reconciliation CSV)

`evidence_reconciliation.json` + `.csv`, `hash_verification.json`, `archive_safety.json`,
`csv_schema_timestamp.json`, `binance_precision_comparison.json`,
`binance_precision_comparison_adapter.json`, `pagination.json`,
`bar_reconstruction_comparison.json`, `bybit_archive_inspection.json`,
`storage_statistics.json`, `provider_coverage.json`, `execution_manifest.json`.
All JSON is deterministic (verified: identical byte hashes across two independent runs).

## Reconciliation result (43 records)

- **present:** 40 — hash-verifiable, byte-size matches manifest.
- **duplicated:** 1 — EV-015 identical content to EV-013 (both Kraken HTML snapshots).
- **missing:** 1 — EV-041 (`token_unlocks/tokenomist_arb.json`) declared but absent on disk.
- **inaccessible:** 1 — EV-019 (OKX) no local_path in manifest.
- **corrupt:** 0, **superseded:** 0.

## Key audit findings (factual, not conclusions)

- All 6 Binance ZIP archives pass `audit_zip_safe` (bounded; compression ratios 3.2–6.4,
  no zip-bomb signature).
- Timestamp-unit inference (`infer_timestamp_unit`):
  - spot aggTrades 2024-12-31 → **millisecond**
  - spot aggTrades 2025-01-01 → **microsecond** (unit change within the archive pair)
  - perp aggTrades 2025-01-01 (sample) → ms; perp trades 2025-01-01 → ms
  - klines 1m 2025-01-01 → **microsecond**; funding 2025-01 → ms
  - 0 malformed across all 120 sampled rows.
- **Headerless Binance precision adapter (runner-level):** mirrors the native comparator
  thresholds using `infer_timestamp_unit`. Both adjacent spot aggTrades archives pass the
  evidence thresholds (50/50 valid, 0 malformed). Result: **ms → us transition supported**
  (TimestampUnit.MILLISECONDS → MICROSECONDS). The native `compare_binance_archive_precision`
  is preserved as FAILED (headerless not supported) — see defects.
- **Bybit pagination replay (static):** 3 pages consumed (initial → p1 → p2 → terminal
  empty), 20 records observed, 0 repeated cursors, 0 gaps, 0 overlaps, 0 ordering
  violations, terminated on `empty_page`. Captured `nextPageCursor` chain is a valid
  forward sequence.
- **Bounded trade-to-bar (Binance, first 10 min 2025-01-01):** reconstruction COMPLETED —
  5437 aggTrades normalized → 10 reconstructed one-minute bars, 0 duplicate trades. The
  runner now completes `compare_bars` against provider candles using explicit comparable
  dimensions (OHLC + base/quote volume) and excludes `trade_count` as semantically
  non-comparable. Binance klines do carry a provider raw-trade count field at index 8,
  but it is explicitly kept distinct from the aggTrades archive record count.
- **Bybit gzip trade archives:** both inspected within limits. Schema
  `timestamp,symbol,side,size,price,tickDirection,trdMatchID,grossValue,homeNotional,
  foreignNotional`; timestamps are Unix seconds with **microsecond fractional part**
  (e.g. 1569974396.557895). Inferred integer-second unit `s`; 0 width/parse failures;
  BTCUSD2019-10-01 truncated at 50,000 sampled rows (1st window only).
- Storage statistics (6 samples, extracted basis): median 74.96 bytes/row; U100 projection
  ≈ 7.92e12 bytes under base assumptions; stress case (200 B/row) ≈ 1.31e13.

## Provider coverage summary (factual only)

- **Binance:** 12 evidence records; archives (spot/perp aggTrades, klines, funding) +
  CHECKSUMs + replacement register + README. Full structured parse of archives above.
- **Bybit:** 8 records; 2 gzip trade archives + instrument/funding JSON snapshots.
- **Coin Metrics:** 7 records; catalog (5991 assets), btc timeseries, error responses
  (bonk SplyCur/SplyIssued unsupported), rate-limit headers, docs.
- **OKX:** 4 records; docs + live funding/trades samples. Bulk host DNS-unreachable
  (no historical files).
- **Kraken:** 3 records, all HTTP **404** at collection (resources not found). See below
  for the DNS-vs-HTTP correction. No bulk files available.
- **DefiLlama:** 6 records; adapters repo at pin `79df37a51d8f26bf4903b04504980e647307c2fc`
  + 4 adapters; emissions API HTTP **402** (paid plan).
- **Tokenomist/Messari:** 3 records; Tokenomist TLS-unreachable, Messari account-gated;
  EV-041 JSON missing on disk.

## Missing evidence / failed or inconclusive checks

- EV-041 Tokenomist ARB JSON missing from staging (TLS-unreachable at collection).
- EV-019 OKX has no staged artifact (DNS-unreachable bulk host).
- Binance native precision comparison inconclusive (toolkit headerless limitation).
- Trade-to-bar comparison partial: reconstruction OK; `compare_bars` blocked by absent
  `trade_count` on klines (structural, not data error).
- Kraken bulk host DNS-unreachable; Kraken documentation URLs returned HTTP 404
  (see correction below).

## Correction to earlier wording (Kraken DNS vs HTTP)

Earlier audit notes loosely described the Kraken failures as "DNS 404". That wording is
incorrect: **DNS failure and HTTP 404 are different layers.**

- The Kraken **documentation URLs** returned **HTTP 404** — the DNS resolved and the
  HTTP server responded, but the specific resources were not found. This is an
  HTTP-layer (application) failure, NOT a DNS failure.
- Separately, the Kraken **bulk-data hosts** (`data.kraken.com` / `download.kraken.com`)
  did **not resolve (DNS)** from this environment.

Both conditions are real and distinct; the compressed "DNS 404" phrasing has been
corrected in this document and in `provider_coverage.json`.

## Limitations

- Audits cover the 43 collected manifest records only; no live re-fetch.
- Storage projections use explicit caller-supplied universe counts (no research-derived
  base universe).
- The native `compare_binance_archive_precision` did not run on real daily dumps
  (headerless); the runner adapter supplied the equivalent evidence instead.
- Trade-to-bar comparison used a bounded 10-minute window, not the full day.

---

## Evidence awaiting Research Lead interpretation

Factual audit outputs requiring Research Lead judgment. **Not** source-acceptance or
rejection decisions; no research hypotheses were revised by this audit.

1. **Binance aggTrades timestamp unit transition (ms → us):** spot aggTrades 2024-12-31
   infers millisecond while 2025-01-01 infers microsecond. Whether the production
   pipeline must handle both units (and the precision-vs-accuracy implication) is a
   Research Lead decision. The runner adapter independently confirms the transition
   (50/50 valid per side; thresholds met).

2. **`compare_binance_archive_precision` cannot run on headerless daily dumps:** the
   toolkit hard-requires `has_header=True`, but Binance daily aggTrades/klines are
   headerless. Escalated as a **potential substantive toolkit defect** — the designed
   adjacent-archive precision check is unusable on real daily dumps without either
   (a) headerless support added to the toolkit, or (b) running on the headed sample
   archives (which are ms, not the transition pair).

3. **`compare_bars` now supports explicit comparable dimensions:** Binance klines expose
   a provider raw-trade count field at index 8, but it is not comparable to the
   reconstruction's aggTrades record count. AUD-005 corrects the comparison contract so
   OHLC + base/quote volume can be compared while `trade_count` is marked not comparable.

4. **Kraken feasibility unassessable:** Kraken documentation URLs returned HTTP 404 and
   the bulk hosts did not resolve (DNS) — two distinct failure layers. No Kraken bulk
   data is available for audit.

5. **Duplicate Kraken evidence (EV-015 == EV-013):** two manifest rows reference
   identical HTML; the manifest double-counts. No content defect.

6. **Missing/inaccessible providers:** Tokenomist (EV-041 missing), OKX (EV-019 no
   artifact), DefiLlama emissions (HTTP 402 paid), Messari (account-gated). Open gaps.

7. **Storage projection assumptions are placeholder:** U25/U50/U100 universe sizes
   (25/50/100) and 1e6 rows/asset/period are illustrative, not research-derived. The
   projection math is validated; the inputs are not a feasibility conclusion.
