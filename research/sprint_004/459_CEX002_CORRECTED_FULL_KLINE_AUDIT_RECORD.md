# CEX-002 Record 459 — Corrected Full Kline Audit Record

- **Date:** 2026-09-02
- **Ticket:** CEX-002
- **Actor:** Jr Dev — Hermes
- **Source authorization:** Review 458
- **Gate 2:** `ACCEPTED`
- **Gate 3:** `IN_PROGRESS`
- **Next required actor:** Lead Quantitative Finance Researcher/Engineer
- **Next ticket:** `NONE`

## Preproof

Hermes reproved the exact preconditions required by Review 458 step 1 before execution:

- `HEAD == origin/main == d23de932ce78135c8b320d56dde3494d476c76ad`.
- Temporary verifier `scripts/research/audit_cex002_record456.py` SHA-256 `0bfae90a2a5c76be1ef1b8389cabda1ca17793eba1d6cc520c94f18ed5464da6`, 730 lines — exactly as accepted by Review 458.
- Both completion files remain the sole entries in their `.complete/` directories:
  - `data/.cex002_bar_1h/.complete/3b803d3e84e5d0bf87064626cc0504e9ff92e225a53ba83cdd4e09c38a2e9fd7.json`
  - `data/.cex002_trade_flow_1h/.complete/a165f9e57065514cadc95620c280a82dbad5032d17c19e1caf012c9d12a84d0a.json`

All preproof checks passed. Execution was authorized.

## Verifier execution

Hermes executed the temporary verifier exactly once from the repository root with bytecode writes disabled, as a single foreground command, and remained attached until terminal:

```text
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python scripts/research/audit_cex002_record456.py
```

- **Exit status:** 0
- **Terminal output line:** `AUDIT RESULT: PASS — all 22,633 partitions per product verified`
- **No retry, second invocation, wrapper, detach, or polling loop occurred.**

## Verified predicates

The corrected verifier performed every predicate required by Review 455 and corrected every defect identified in Review 457. The following were verified against the two accepted completion descriptors and the physical artifact trees:

### [0] Staging and process
- Both `.staging/` directories (bar, trade-flow) are empty.
- No live Python process with the exact relative or absolute kline-normalizer script argument was found by reading `/proc/*/cmdline` directly.

### [1] Completion files
- Each `.complete/` directory contains exactly one entry.
- Each completion file is a regular non-symlink file.
- Each full-file SHA-256 equals both its content-addressed filename and the accepted completion identity.

### [2] Descriptor top-level facts
- Both descriptors name exactly 22,633 unique `(native_symbol, utc_month)` partition entries, unique canonical relative Parquet paths, and unique lineage paths.
- Accepted document type, normalizer source SHA-256, schema version, schema SHA-256, source count, source bytes, sources SHA-256, writer identity, required product, authorities-authenticated flag, row equation, volume-invariant failures, and quality-gap artifact fields all match the accepted constants.
- Aggregate descriptor row counts: bar 16,033,469; trade-flow 16,033,442.

### [3] Full partition audit (22,633 per product)
For every partition entry in both products:
- The descriptor path is a non-absolute canonical `PurePosixPath` with no empty, dot, or parent component; matches the exact `.partitions/<symbol>/<month>/<sha>.parquet` or `.lineage/<symbol>/<month>/<sha>.json` shape; resolves beneath the fixed product root; and traverses no symlinked component.
- The referenced Parquet is a regular non-symlink file; its full-file SHA-256 equals both the descriptor value and its content-addressed filename; its actual `ParquetFile.schema_arrow` equals the accepted `BAR_SCHEMA` (bar) or `TRADE_FLOW_SCHEMA` (trade-flow) including metadata; and its metadata row count equals the descriptor row count.
- The referenced lineage document is a regular non-symlink file; its full-file SHA-256 equals both the descriptor value and its content-addressed filename; and its parsed `document_type`, `required_product`, `native_symbol`, `utc_month`, `row_count`, `parquet_sha256`, `schema_sha256`, `writer_identity`, `schema_version`, and `parquet_name` fields all agree with the descriptor entry and accepted constants.

### [4] Aggregate row counts
- Bar: 16,033,469 product rows (16,033,509 physical - 40 excluded).
- Trade-flow: 16,033,442 product rows (16,033,509 physical - 67 excluded).

### [5] Quality-gap artifacts
- Each quality-gap Parquet is a regular non-symlink file; its full-file SHA-256 equals the accepted value; its actual schema equals `QUALITY_GAP_SCHEMA` including metadata; its row count equals the accepted value and does not exceed the 181-row ceiling; and its materialized rows equal its metadata row count.
- Recomputed `missing_grid_points` (sum of `expected_grid_count`) equals the accepted value:
  - Bar: 154 gap rows, 8,043 missing grid points.
  - Trade-flow: 181 gap rows, 8,070 missing grid points.
- Each quality-gap lineage document is a regular non-symlink file; its full-file SHA-256 equals the accepted value; its parsed `document_type`, `required_product`, `row_count`, `missing_grid_points`, and `provider_invalid_exclusion_count` fields match accepted constants; and its canonical exclusion-list hash recomputes from the recorded rows.

### [6] Exclusion sets and one-to-one gap/exclusion equality
- Bar exclusion identities: 40.
- Trade-flow exclusion identities: 67.
- Bar exclusion set is a subset of trade-flow; trade-flow-only count: 27.
- Provider-invalid gap keys and exclusion-lineage keys are exactly equal as sets; no duplicate keys on either side; every gap key is an exact one-hour key (`missing_run_start_ms == end`, `expected_grid_count == 1`, `gap_kind == provider_invalid_required_fields`); key count equals the accepted excluded-row count per product.

### [7] Physical inventory (referenced vs. unreferenced)

**Bar root (`data/.cex002_bar_1h`):**
- Referenced: 22,633 Parquets + 22,633 lineages + 1 quality-gap Parquet + 1 quality-gap lineage + 1 completion = 45,268 files.
- Physical walk: 22,664 Parquets + 42,968 lineages + 1 quality-gap Parquet + 1 quality-gap lineage + 1 completion = 65,634 files.
- Unreferenced: 20,366 files (31 Parquets + 20,335 lineages).

**Trade-flow root (`data/.cex002_trade_flow_1h`):**
- Referenced: 22,633 Parquets + 22,633 lineages + 1 quality-gap Parquet + 1 quality-gap lineage + 1 completion = 45,268 files.
- Physical walk: 22,680 Parquets + 42,968 lineages + 1 quality-gap Parquet + 1 quality-gap lineage + 1 completion = 65,650 files.
- Unreferenced: 20,382 files (47 Parquets + 20,335 lineages).

Physical inventories explicitly separate descriptor-referenced files from older unreferenced content-addressed files.

## Exact completion identities

- **Bar 1h:** 22,633 partitions, 16,033,509 physical rows, 16,033,469 product rows, 40 excluded rows, 154 quality-gap rows, 8,043 missing grid points; completion SHA-256 `3b803d3e84e5d0bf87064626cc0504e9ff92e225a53ba83cdd4e09c38a2e9fd7`; schema SHA-256 `12af135c756ae5046961c7dc2eb4177506801b6b42ffe9f0f7a5c970fdd644eb`.
- **Trade flow 1h:** 22,633 partitions, 16,033,509 physical rows, 16,033,442 product rows, 67 excluded rows, 181 quality-gap rows, 8,070 missing grid points; completion SHA-256 `a165f9e57065514cadc95620c280a82dbad5032d17c19e1caf012c9d12a84d0a`; schema SHA-256 `0e0903f5a79396f80f879ee33ea898d2008bace08271c2e0151295a18e83a68f`.

## Post-audit capacity observation

One new exact audit-time capacity observation obtained after the verifier went terminal:

```text
df -B1 --output=avail data
22741000192
```

Available bytes on `data`: **22,741,000,192**. This is labeled as a post-audit observation, not as reconstructed run-time evidence.

## Temporary-file removal proof

Hermes removed exactly the untracked temporary verifier and proved its absence:

- `test ! -e scripts/research/audit_cex002_record456.py` — path absent.
- `git ls-files scripts/research/audit_cex002_record456.py | wc -l` returned 0 — path unstaged and untracked.

No other file or directory was removed or cleaned.

## Corrections to prior records

### Record 454 corrections
1. **Chronology:** Record 454 stated `HEAD == origin/main == 5a3bd73e...` "before the integration commit," but `5a3bd73e10fc208bdb43b5334b097a264d2dbb9b` is the integration commit itself. The actual pre-integration review publication was `f34c550b9d7ec0cc1c44c590d20e3b073b551bcd`; `5a3bd73e...` was the post-integration head.
2. **Capacity labels:** Record 454's preflight and terminal available-space fields contained literal `?` digits — default `df` KiB counts, not exact byte counts. The exact historical values cannot be reconstructed from truncated text. Review 453 already recorded an exact 35,803,824,128-byte reviewer observation before Hermes began. Capacity did not stop the successful run.

### Record 456 corrections
Record 456 claimed a complete audit but its verifier omitted several checks required by Review 455 and then remained as an untracked repository file. The corrected verifier in this record now performs every omitted predicate:
1. Compares every referenced partition's actual `ParquetFile.schema_arrow` to the exact accepted `BAR_SCHEMA` or `TRADE_FLOW_SCHEMA` (Record 456 read only metadata row counts).
2. Compares each quality-gap Parquet's actual schema to `QUALITY_GAP_SCHEMA`, reads its bounded rows, and recomputes row count and `missing_grid_points` (Record 456 did none of these).
3. Builds exact provider-invalid gap keys and proves one-to-one set equality with exclusion-lineage keys, rejecting duplicates on either side (Record 456 checked only identity-set sizes and subset relation).
4. Requires every descriptor path to be canonical relative POSIX, match the exact shape, resolve beneath the fixed product root, and traverse no symlinked component (Record 456 joined paths without these checks).
5. Reads `/proc/*/cmdline` directly and rejects any live Python command whose argument is the exact normalizer path (Record 456 checked staging only, not processes).
6. Stops immediately on the first mismatch with a nonzero exit (Record 456 accumulated mismatches and continued).

Record 456's reported zero hash mismatches are preserved as bounded evidence that all referenced files are present and byte-identical. The additional predicates above were not established by Record 456 and are established here.

## Authorization boundary

No normalizer, test, source/test/CLI edit, data change, download, network, wrapper, detach, polling loop, retry, general cleanup, catalog, NautilusTrader, experiment, model, Harmonic Trader, other product, PAPER, LIVE, or next-ticket work was authorized or performed. Gate 2 remains accepted; Gate 3 and CEX-002 remain `IN_PROGRESS`; next ticket remains `NONE`.

Both actor fields return to the Lead Quantitative Finance Researcher/Engineer.
