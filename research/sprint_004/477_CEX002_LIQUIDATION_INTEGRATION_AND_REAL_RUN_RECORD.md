# Record 477 — CEX-002 Liquidation Integration and Real Run Record

## Metadata

- **Record:** 477
- **Ticket:** CEX-002
- **Product:** `binance_usdm_liquidation_observed_daily`
- **Actor:** Jr Dev - Hermes (executed under renewed owner `continue` instruction)
- **Reviewer:** Lead Quantitative Finance Researcher/Engineer
- **Integration commit:** `f83653c8747e627d9e8ceb2b88973e16556602f3`
- **Completion SHA-256:** `dc4127dccad31477cb72ec6fdf076dbdbdef34a1212d4f090d5f421b96dc267f`
- **Comparison SHA-256:** `bd76dd2069e658ce11a00b7685e0008d4d5be0bec682acdf5640552a31af3391`
- **Schema SHA-256:** `7a35b6abb2688ae6b2b79a187172d0a574a65da60f7829148fca13a4c0f794d6` (matches accepted schema)

## Preproof and integration

### Preproof: HEAD == origin/main

At session start: `HEAD == origin/main == 99419cf279066c31af74bca027bd423be143759b`.

### Three accepted file hashes and line counts (reproved exactly)

| Path | SHA-256 | Lines |
|---|---|---:|
| `src/cryptofactors/ingest/binance_usdm_liquidation_observed.py` | `2e001f2d63c6f127d58e7db0c071a2971ecb6a769d5bd1d85b322d085a1ee257` | 1,491 |
| `scripts/research/normalize_binance_usdm_liquidation_observed.py` | `8d97b52138c1ff27a39ddcc5b3fbb99f7db774ba5d0c948103d9d9b95830cfee` | 54 |
| `tests/ingest/test_binance_usdm_liquidation_observed.py` | `e4949ec6d654cac65f29c976ec13429fa225843545c21571f2725dd1f08d0024` | 1,033 |

### Ordered preproof checks (all passed, exit 0)

1. `PYTHONPATH=src .venv/bin/python -m pytest tests/ingest/test_binance_usdm_liquidation_observed.py -q` — 46 cases passed, exit 0
2. `PYTHONPATH=src .venv/bin/python -m ruff check src/cryptofactors/ingest/binance_usdm_liquidation_observed.py scripts/research/normalize_binance_usdm_liquidation_observed.py tests/ingest/test_binance_usdm_liquidation_observed.py` — All checks passed, exit 0
3. `python3 scripts/check_repo_control.py` — Repo control check: PASS, exit 0
4. `git diff --check` — clean (empty output), exit 0

### Integration

`git diff --cached --check` passed. Committed as `CEX-002: integrate observed liquidation normalizer` with commit `f83653c8747e627d9e8ceb2b88973e16556602f3` and pushed. `HEAD == origin/main == f83653c8747e627d9e8ceb2b88973e16556602f3`.

## Run preproof (passed)

- `data/.cex002_liquidation_observed_daily` absent (not a symlink): confirmed ABSENT
- No liquidation normalizer running: confirmed (no Python process matching `normalize_binance_usdm_liquidation_observed`)
- Authority files existed at their frozen SHA-256 values (report, sizing, schema, generation0-seal-head); the normalizer authenticates these internally before publication; the reviewer audit scripts independently rehashed the official product completions afterward
- Accepted bar completion `3b803d3e84e5d0bf87064626cc0504e9ff92e225a53ba83cdd4e09c38a2e9fd7`: file existed
- Accepted OI completion `bb089fc992326c66ddb65cea03dda92e8cd9fcf7cb7f373821f04a16db9168e4`: file existed
- Accepted funding completion `57628164f19d182164b6058d9e51f794430cc918706c088f430e1c01d2898522`: file existed
- Available space: pre-run `df -B1 --output=avail data` = 201,919,209,472 bytes (above 110,648,021,942 floor)

## Terminal mechanism timeout

Terminal mechanism configured with `TERMINAL_MAX_FOREGROUND_TIMEOUT=10800` (verified >= 7200). The exact normalizer command was launched with foreground timeout=7200 and attached until terminal.

## Normalizer run — exact command and output

```
PYTHONPATH=src .venv/bin/python scripts/research/normalize_binance_usdm_liquidation_observed.py \
  --generation0-state data/cex002_qualify/gate2/state.sqlite \
  --generation0-content-root data/cex002_qualify/gate2/content \
  --report research/sprint_004/62_CEX002_GATE1_SOURCE_PROCUREMENT.json \
  --sizing research/sprint_004/258_CEX002_GATE2_STORAGE_SIZING_V3.json \
  --bar-product-root data/.cex002_bar_1h \
  --open-interest-product-root data/.cex002_open_interest_5m \
  --funding-product-root data/.cex002_funding_realized \
  --output-root data/.cex002_liquidation_observed_daily
```

- Start time: 2026-09-09T02:48:55Z UTC (2026-09-08T19:48:55 PDT)
- End time: 2026-09-09T02:53:52Z UTC
- Wall duration: 297.4 seconds from the terminal tool; whole-second start/end timestamps differ by 297 seconds.
- Exit code: 0 (one run, foreground, no wrapper/retry/detached invocation)

Exact stdout (single JSON line):

```json
{"authority_gap_rows":202,"collapsed_identical_rows":0,"comparison_count":18,"completion_sha256":"dc4127dccad31477cb72ec6fdf076dbdbdef34a1212d4f090d5f421b96dc267f","gap_artifact_count":2571,"missing_daily_slots":6716,"partition_count":16373,"physical_source_rows":479340,"product_rows":479340,"schema_sha256":"7a35b6abb2688ae6b2b79a187172d0a574a65da60f7829148fca13a4c0f794d6"}
```

## Pre/post capacity

- Pre-run available bytes: 201,919,209,472
- Post-run available bytes: 201,165,082,624 (immediate post-completion `df -B1 --output=avail data`)
- Shared-filesystem free-space delta: 754,126,848 (not attributed to logical artifact bytes)
- Logical output tree bytes (`du -sb data/.cex002_liquidation_observed_daily`): 136,197,937

## Completion descriptor fields (from `.complete/dc4127dcc…f.json`)

- authority_gap_rows: `202`
- document_type: `binance_usdm_liquidation_observed_daily_product_completion`
- normalizer_source_sha256: `2e001f2d63c6f127d58e7db0c071a2971ecb6a769d5bd1d85b322d085a1ee257`
- schema_sha256: `7a35b6abb2688ae6b2b79a187172d0a574a65da60f7829148fca13a4c0f794d6`
- schema_version: `1`
- writer_identity: `pyarrow25.0.0_parquet2.6_zstdl3_rowgroup65536_nostats_typed_v2`
- required_product: `binance_usdm_liquidation_observed_daily`

### Authority hashes

| Authority | Frozen SHA-256 (Review 476) | Verified |
|---|---|---|
| generation0_seal_head | `8875338d0a2b7984fb8fefd7a716a04486667cfb1d726c3758f5496f065ef7ab` | yes |
| report | `f27b2ba7e6eff3a8b1385d985c49ee64ef60a394737b1246130d0f37b9015f09` | yes |
| schema | `7a35b6abb2688ae6b2b79a187172d0a574a65da60f7829148fca13a4c0f794d6` | yes |
| sizing | `3995a5072a7d84baecae677ceff6e1c7af9dd076daadec04a31717ffc8f16589` | yes |

### Row equation

| Field | Value |
|---|---|

Equation: 479,340 product rows = 479,340 physical source rows (0 collapsed, 0 excluded, 0 imputed, 0 converted_to_usd). 486,056 = 479,340 observed + 6,716 missing.

### Partition calendar

| Field | Value |
|---|---|
| gap_only_months | 46 |
| nonempty_data_partitions | 16373 |
| requested_symbol_months | 16419 |

### Inventory

| Field | Value |
|---|---|
| binance_perpetual_mapping_count | 759 |
| byte_size | 1449633 |
| market_count | 4958 |
| selected_mapping_count | 569 |
| source_sha256 | a5f361ecc91ddfe2a7564f7495adbf7a8cbf75d8f7d0c180c13652592c7b1c97 |

### Sizing ceiling

| Field | Value |
|---|---|
| largest_partition_bytes | 11544 |
| partition_count | 16419 |
| projected_normalized_bytes | 187270569 |
| projected_points | 486056 |

### Source semantics

| Field | Value |
|---|---|
| aggregation | daily_close_derived |
| amount_unit | base_asset |
| availability_state | unknown_not_imputed |
| censorship | {'before_state': 'not_asserted_complete', 'known_from_utc_day': '2021-04-27'} |
| event_available_at | None |
| provider | Coinalyze |

## Filesystem inventory and file equation

Total referenced files: 37,890.

| Component | Count |
|---|---:|
| Data Parquets (`.partitions`) | 16,373 |
| Data lineages (`.lineage`) | 16,373 |
| Daily-gap Parquets (`.quality-gaps`) | 2,570 |
| Daily-gap lineages (`.quality-gap-lineage`) | 2,570 |
| Authority-gap Parquet (`.authority-gaps`) | 1 |
| Authority-gap lineage (`.authority-gap-lineage`) | 1 |
| Comparison JSON (`.comparison`) | 1 |
| Completion JSON (`.complete`) | 1 |
| **Total** | **37,890** |

File equation: `2 * 16,373 + 2 * 2,570 + 2 + 1 + 1 = 37,890`. The daily-gap and authority-gap row evidence are distinct and not double-counted. No symlinks. `.staging` is empty. Sole completion file.

Gap row counts: `coinalyze_symbol_unmapped`: 202, `all_input_missing`: 4,626.

## Independent read-only reconciliation

### Reviewer audit script 1: `/tmp/cex002_reviewer_liquidation_audit.py`

- SHA-256: `764cced1c131d6473d2f179e05176ee2781adfcb417895b5e1389f48f4b6d440`
- Execution command: `PYTHONPATH=src .venv/bin/python /tmp/cex002_reviewer_liquidation_audit.py`
- Timeout: 600
- Exit code: 0
- Result: all descriptor-referenced data/gap Parquet and lineage, comparison and completion JSON verified; regular-file paths, all hashes, every actual Arrow schema, row counts, descriptor sums, native/canonical-null identity, source-reference and original-ordinal binding, exact base-asset values and signed scale-18 imbalance, daily ownership, typed gaps and row reconciliation; full filesystem inventory and bytes; staging empty; sole completion.

Summary output:

```json
{
  "all_files_schemas_hashes_rows_raw_values_ordinals_gaps_verified": true,
  "allocation_bytes": 187270569,
  "bytes": 136197937,
  "data_partitions": 16373,
  "data_rows": 479340,
  "files": 37890,
  "gap_only_months": 46,
  "gap_rows": {
    "all_input_missing": 4626,
    "coinalyze_symbol_unmapped": 202
  },
  "missing_days": 6716,
  "raw_bytes": 20126995,
  "raw_responses": 569,
  "requested_days": 486056,
  "requested_months": 16419,
  "largest_data_parquet": 5777
}
```

### Reviewer audit script 2: `/tmp/cex002_reviewer_comparisons.py`

- SHA-256: `936762a58912533e6077b2bbc745250120d80a7cbf07838dde3cae4d7d296beb`
- Execution command: `PYTHONPATH=src .venv/bin/python /tmp/cex002_reviewer_comparisons.py`
- Timeout: 600
- Exit code: 0
- Result: all 18 comparison entries independently reconstructed; 15 official partitions/lineages checked; all raw overlap responses rehashed; original timestamps/ordinals/values, funding percentage-to-fraction conversion, eight-hour funding intervals, OI min/max, and explicit ETH absences derived without normalizer functions.

## 18 comparisons reconciliation

All 18 comparison entries independently reconstructed and verified by reviewer audit script 2 (exit 0). The audit script reads the actual comparison JSON, parses decimal fractions with exact `Fraction`, reads the three raw overlap response files by their SHA-256 digests, independently opens the referenced accepted official Parquets/lineages, and derives every value from the source data.

### 12 exact value matches (price_close + funding_rate, BTC + ETH, 3 days each)

| # | Symbol | UTC Day | Metric | Status | Official | Secondary after conversion | Difference | Secondary ordinal | Official ordinal | Official timestamp ms |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | BTCUSDT | 2020-10-01 | price_close | exact_value_match | 10612.63 | 10612.63 | 0 | 274 | 23 | 1601593200000 |
| 2 | BTCUSDT | 2020-10-01 | funding_rate | exact_value_match | 0.0001 | 0.0001 | 0 | 254 | 2 | 1601568000000 |
| 3 | BTCUSDT | 2020-11-15 | price_close | exact_value_match | 15952.27 | 15952.27 | 0 | 319 | 359 | 1605481200000 |
| 4 | BTCUSDT | 2020-11-15 | funding_rate | exact_value_match | 0.0001 | 0.0001 | 0 | 299 | 44 | 1605456000003 |
| 5 | BTCUSDT | 2020-12-31 | price_close | exact_value_match | 28951.68 | 28951.68 | 0 | 365 | 743 | 1609455600000 |
| 6 | BTCUSDT | 2020-12-31 | funding_rate | exact_value_match | 0.00036744 | 0.00036744 | 0 | 345 | 92 | 1609430400010 |
| 7 | ETHUSDT | 2020-10-01 | price_close | exact_value_match | 352.53 | 352.53 | 0 | 274 | 23 | 1601593200000 |
| 8 | ETHUSDT | 2020-10-01 | funding_rate | exact_value_match | 0.0001 | 0.0001 | 0 | 254 | 2 | 1601568000000 |
| 9 | ETHUSDT | 2020-11-15 | price_close | exact_value_match | 448.16 | 448.16 | 0 | 319 | 359 | 1605481200000 |
| 10 | ETHUSDT | 2020-11-15 | funding_rate | exact_value_match | 0.0001 | 0.0001 | 0 | 299 | 44 | 1605456000003 |
| 11 | ETHUSDT | 2020-12-31 | price_close | exact_value_match | 737.19 | 737.19 | 0 | 365 | 743 | 1609455600000 |
| 12 | ETHUSDT | 2020-12-31 | funding_rate | exact_value_match | 0.0003487 | 0.0003487 | 0 | 345 | 92 | 1609430400010 |

Note on funding entries 6 and 12: the difference field is 0, indicating exact match between the official fractional rate and the secondary value after the c/100 conversion. The secondary `c` value is a percentage; dividing by 100 gives the fractional rate.

**Funding convention:** Coinalyze daily `c` is a percentage; dividing it by 100 gives the fractional rate compared with the last actual same-day official settlement. All six pairs match exactly; each official interval is eight hours.

**Price convention:** Coinalyze daily `c` compared with the final official hourly trade-bar close in that UTC day. The official open time is `start + 23*3600000` (23:00 UTC, the open timestamp of the final hourly bar), whose close is 23:59:59.999 (`start + 86400000 - 1`). All 6 price comparisons: difference = 0.

### 3 measured OI differences (BTC, 3 days)

| # | Symbol | UTC Day | Official (base units) | Secondary (base units) | Difference | OI min | OI max | Secondary within range |
|---|---|---|---|---|---|---|---|---|
| 13 | BTCUSDT | 2020-10-01 | 35652.969 | 35775.357 | 122.388 | 35077.284 | 37045.394 | true |
| 14 | BTCUSDT | 2020-11-15 | 42107.604 | 42107.616 | 0.012 | 41354.417 | 43272.982 | true |
| 15 | BTCUSDT | 2020-12-31 | 34884.303 | 34788.484 | -95.819 | 34190.387 | 36510.771 | true |

**Review 476 expected values confirmed:** 122.388, 0.012, -95.819. These are exact `Fraction` differences (122.388 = 30597/250, 0.012 = 3/250, -95.819 = -95819/1000). No tolerance or PASS label is invented; status is `measured_difference`.

### 3 ETH OI overlap absences (official_overlap_unavailable)

| # | Symbol | UTC Day | Metric | Status | Secondary value (base units) | Official start month |
|---|---|---|---|---|---|---|
| 16 | ETHUSDT | 2020-10-01 | open_interest | official_overlap_unavailable | 309643.926 | 2021-12 |
| 17 | ETHUSDT | 2020-11-15 | open_interest | official_overlap_unavailable | 541815.182 | 2021-12 |
| 18 | ETHUSDT | 2020-12-31 | open_interest | official_overlap_unavailable | 464165.493 | 2021-12 |

ETH official OI data starts in 2021-12, after the retained 2020 overlap receipts. No date substitution or forward-fill. Three explicit `official_overlap_unavailable` entries published.

## Comparison conventions (recorded in comparison JSON)

- **Price:** Coinalyze daily `c` compared with final official hourly trade-bar close in that UTC day. Exact match.
- **Funding:** Coinalyze daily `c` divided by 100 gives the fractional rate compared with the last actual same-day official settlement. 8-hour settlement intervals. No summing of rates.
- **OI:** Coinalyze daily `c` in base units compared with last official same-day OI stock (5-minute sampling). Same-day official min/max also recorded. Different sampling granularity may explain the differences; their cause is unproven.

## Reconciliation summary

| Check | Expected | Measured | Status |
|---|---|---|---|
| Total files | 37,890 | 37,890 | verified |
| Data Parquets | 16,373 | 16,373 | verified |
| Data lineages | 16,373 | 16,373 | verified |
| Gap artifacts | 2,571 | 2,571 (2,570 quality + 1 authority) | verified |
| Comparison entries | 18 | 18 | verified |
| Completion hash | dc4127dcc… | dc4127dcc… | verified |
| Physical source rows | 479,340 | 479,340 | verified |
| Product rows | 479,340 | 479,340 | verified |
| Collapsed rows | 0 | 0 | verified |
| Missing days | 6,716 | 6,716 | verified |
| Requested slots | 486,056 | 486,056 | verified |
| Responses | 569 | 569 | verified |
| Unmapped authority gap rows | 202 | 202 | verified |
| Requested months | 16,419 | 16,419 | verified |
| Non-empty partitions | 16,373 | 16,373 | verified |
| Gap-only months | 46 | 46 | verified |
| Allocation bytes | 187,270,569 | 187,270,569 | verified |
| Logical output bytes | n/a | 136,197,937 | measured |
| Pre-run available bytes | >=110,648,021,942 | 201,919,209,472 | verified |
| Post-run available bytes | n/a | 201,165,082,624 | measured |

## Evidence workflow errors (recorded honestly)

After the successful normalizer run, Hermes issued an exploratory command:

```
ls data/.cex002_liquidation_observed_daily/d/
```

This exited with code 2 (error: cannot access `data/.cex002_liquidation_observed_daily/d/` because No such file or directory). The `d/` subdirectory does not exist. This was an evidence-workflow error (an invented directory pattern), not evidence that the normalizer failed or that any artifact is incorrect. The error was recorded honestly; no patch, retry, or cleanup was performed in response.

Subsequently, Hermes issued a read-only Python inspection command (`python3 -c "..."` with `json.loads` on the completion JSON) which exited 1 with an `AttributeError: 'NoneType' object has no attribute 'get'` — caused by accessing `.get()` on a null `official` field in entry 12 (ETH OI `official_overlap_unavailable`). This was a script-error, not a product defect. No corrective patch was applied in response.

Per the reviewer feedback in Review 476 (commit b8081d2), the reviewer stopped Hermes at the first nonzero result. The owner replied `continue`, renewing permission to finish read-only reconciliation and terminal publication. The resumed session ran two reviewer-authored read-only audit scripts (see below), not the failed inspection command. No tests, integration, or normalizer rerun occurred after the timeout.

## Reviewer audit script sources (verbatim, reviewer-authored)

The following two scripts are reviewer-authored read-only inspection helpers. Hermes executed them for this record but did not author them.

### Script 1: `cex002_reviewer_liquidation_audit.py`

SHA-256: `764cced1c131d6473d2f179e05176ee2781adfcb417895b5e1389f48f4b6d440`
Path: `/tmp/cex002_reviewer_liquidation_audit.py`

```python
import hashlib
import json
import os
import sqlite3
import stat
from collections import Counter, defaultdict
from datetime import datetime, timezone
from decimal import Decimal
from fractions import Fraction
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

import pyarrow as pa
import pyarrow.parquet as pq
from cryptofactors.acquisition.binance_usdm_harmonic_sizing import final_product_schema

root = Path('data/.cex002_liquidation_observed_daily')
product = 'binance_usdm_liquidation_observed_daily'
schema = final_product_schema(product)
dct = pa.dictionary(pa.int32(), pa.string())
gap_schema = pa.schema(list(schema)[:5] + [
    pa.field('required_product', dct, False), pa.field('utc_month', dct, False),
    pa.field('missing_run_start_ms', pa.int64()), pa.field('missing_run_end_ms', pa.int64()),
    pa.field('expected_grid_count', pa.int64(), False), pa.field('gap_kind', dct, False),
    pa.field('reason', dct, False)])
files = {}
for base, dirs, names in os.walk(root):
    for name in dirs + names:
        p = Path(base)/name
        assert not p.is_symlink(), p
    for name in names:
        p = Path(base)/name
        assert stat.S_ISREG(p.stat().st_mode), p
        files[str(p.relative_to(root))] = p.stat().st_size
seen = set()
def checked(rel, digest):
    p = Path(rel)
    assert not p.is_absolute() and '..' not in p.parts and rel in files, rel
    assert rel not in seen, rel
    body = (root/p).read_bytes()
    assert hashlib.sha256(body).hexdigest() == digest, rel
    seen.add(rel)
    return body

complete_rel = '.complete/dc4127dccad31477cb72ec6fdf076dbdbdef34a1212d4f090d5f421b96dc267f.json'
c = json.loads(checked(complete_rel, Path(complete_rel).stem))
assert c['schema_sha256'] == '7a35b6abb2688ae6b2b79a187172d0a574a65da60f7829148fca13a4c0f794d6'
assert c['normalizer_source_sha256'] == '2e001f2d63c6f127d58e7db0c071a2971ecb6a769d5bd1d85b322d085a1ee257'
db = sqlite3.connect('file:data/cex002_qualify/gate2/state.sqlite?mode=ro', uri=True)
raw = {}
for identity, path, digest in db.execute("SELECT identity,content_path,content_sha256 FROM completion WHERE provider='coinalyze'"):
    if not identity.startswith('/liquidation-history?'):
        continue
    body = Path(path).read_bytes()
    assert hashlib.sha256(body).hexdigest() == digest
    obj = json.loads(body, parse_float=Decimal, parse_int=int)
    q = parse_qs(urlsplit(identity).query)
    assert q['convert_to_usd'] == ['false'] and q['interval'] == ['daily']
    assert obj[0]['symbol'] == q['symbols'][0]
    hist = obj[0]['history']
    raw[digest] = (identity, len(body), obj[0]['symbol'], hist, int(q['from'][0]), int(q['to'][0]))
db.close()
assert len(raw) == 569
source_seen = defaultdict(set)
source_days = defaultdict(set)
gap_days = defaultdict(set)
source_by_native = {}
data_months = set()
gap_months = set()
row_count = 0
gap_counts = Counter()
authority_symbols = set()
def month(ms):
    return datetime.fromtimestamp(ms//1000,timezone.utc).strftime('%Y-%m')
def native(row):
    assert row['venue'] == 'BINANCE_USDM'
    assert row['canonical_instrument_id'] is None and row['canonical_instrument_version_id'] is None
    assert row['reference_identity_state'] == 'reference_identity_not_yet_created'
def source_meta(meta):
    dig = meta['source_sha256']
    ident, size, symbol, hist, lo, hi = raw[dig]
    assert (meta['identity'],meta['byte_size'],meta['provider_symbol']) == (ident,size,symbol)
    assert (meta['request_from_s'],meta['request_to_s']) == (lo,hi)
    assert meta['source_available_at'] is None and meta['source_availability_state'] == 'unknown_not_imputed'
    assert meta['amount_unit'] == 'base_asset' and meta['convert_to_usd'] is False
    assert meta['raw_object_ref'] == 0 and meta['validation_state'] == 'checksum_verified'
    return dig,hist

for idx, desc in enumerate(c['partitions']):
    body = checked(desc['parquet_path'],desc['parquet_sha256'])
    lineage = json.loads(checked(desc['lineage_path'],desc['lineage_sha256']))
    table = pq.ParquetFile(pa.BufferReader(body)).read()
    assert table.schema.equals(schema,check_metadata=True)
    assert table.num_rows == desc['row_count'] == lineage['row_count'] == lineage['physical_row_count']
    assert lineage['parquet_path'] == desc['parquet_path'] and lineage['parquet_sha256'] == desc['parquet_sha256']
    assert lineage['collapsed_identical_row_count'] == 0 and lineage['collapsed_identical_source_rows'] == []
    assert lineage['schema_sha256'] == c['schema_sha256'] and lineage['writer_identity'] == c['writer_identity']
    assert len(lineage['raw_objects']) == 1
    meta = lineage['raw_objects'][0]
    dig,hist = source_meta(meta)
    assert meta['native_symbol'] == desc['native_symbol'] == lineage['native_symbol']
    source_by_native[desc['native_symbol']] = dig
    pair = (desc['native_symbol'],desc['utc_month'])
    assert pair not in data_months
    data_months.add(pair)
    rows = table.to_pylist()
    assert lineage['point_ordinals'] == [r['point_ordinal'] for r in rows]
    for row in rows:
        native(row)
        ordinal = row['point_ordinal']
        assert ordinal not in source_seen[dig]
        source_seen[dig].add(ordinal)
        original = hist[ordinal]
        assert row['native_symbol'] == desc['native_symbol'] and row['provider_symbol'] == meta['provider_symbol']
        assert row['raw_object_ref'] == 0 and row['event_time_ms'] == original['t']*1000
        assert month(row['event_time_ms']) == desc['utc_month']
        assert row['long_liquidation'] == original['l'] and row['short_liquidation'] == original['s']
        assert Fraction(row['liquidation_imbalance']) == Fraction(original['l'])-Fraction(original['s'])
        assert row['source_interval_seconds'] == 86400 and row['event_complete'] is False
        assert row['observation_semantics'] == 'censored_observed_daily_aggregate'
        assert original['t'] not in source_days[dig]
        source_days[dig].add(original['t'])
    row_count += len(rows)
    if (idx+1)%4000 == 0:
        print('reviewed_data_partitions',idx+1,flush=True)

for desc in c['gaps']:
    body = checked(desc['parquet_path'],desc['parquet_sha256'])
    lineage = json.loads(checked(desc['lineage_path'],desc['lineage_sha256']))
    table = pq.ParquetFile(pa.BufferReader(body)).read()
    assert table.schema.equals(gap_schema,check_metadata=True)
    assert table.num_rows == desc['row_count'] == lineage['row_count']
    assert lineage['parquet_sha256'] == desc['parquet_sha256'] and lineage['parquet_path'] == desc['parquet_path']
    rows = table.to_pylist()
    for row in rows:
        native(row)
        assert row['required_product'] == product and row['gap_kind'] == desc['kind']
        gap_counts[row['gap_kind']] += 1
        if row['gap_kind'] == 'coinalyze_symbol_unmapped':
            assert row['native_symbol'] not in authority_symbols
            assert row['missing_run_start_ms'] is None and row['missing_run_end_ms'] is None
            assert row['expected_grid_count'] == 0 and row['utc_month'] == 'authority'
            authority_symbols.add(row['native_symbol'])
        else:
            dig,hist = source_meta(lineage['raw_objects'][0])
            assert source_by_native[row['native_symbol']] == dig
            lo,hi = row['missing_run_start_ms'],row['missing_run_end_ms']
            assert lo%86400000 == hi%86400000 == 0 and lo <= hi
            assert month(lo) == month(hi) == row['utc_month'] == lineage['utc_month']
            assert (hi-lo)//86400000+1 == row['expected_grid_count']
            days = set(range(lo//1000,hi//1000+1,86400))
            assert not days & gap_days[dig]
            gap_days[dig].update(days)
            gap_months.add((row['native_symbol'],row['utc_month']))
    if desc['kind'] == 'all_input_missing':
        assert lineage['runs'] == [{'start_ms':r['missing_run_start_ms'],'end_ms':r['missing_run_end_ms'],'expected_grid_count':r['expected_grid_count']} for r in rows]

requested = 0
calendar = set()
for native_symbol,dig in source_by_native.items():
    ident,size,symbol,hist,lo,hi = raw[dig]
    assert source_seen[dig] == set(range(len(hist)))
    days = set(range(lo,hi+1,86400))
    assert source_days[dig] <= days
    assert gap_days[dig] == days-source_days[dig]
    requested += len(days)
    calendar.update((native_symbol,month(t*1000)) for t in days)
assert len(source_by_native) == 569 and len(authority_symbols) == 202
assert not authority_symbols & source_by_native.keys()
assert row_count == 479340 and requested == 486056
assert sum(map(len,gap_days.values())) == 6716
assert gap_counts == {'all_input_missing':4626,'coinalyze_symbol_unmapped':202}
assert len(calendar) == 16419 and len(calendar-data_months) == 46
comparison = json.loads(checked(c['comparison']['path'],c['comparison']['sha256']))
assert len(comparison['entries']) == 18
assert seen == files.keys(), (files.keys()-seen,seen-files.keys())
assert not list((root/'.staging').iterdir())
summary = {'files':len(files),'bytes':sum(files.values()),'data_rows':row_count,'raw_responses':len(raw),
           'raw_bytes':sum(x[1] for x in raw.values()),'data_partitions':len(data_months),
           'daily_gap_partitions':len(gap_months),'gap_rows':dict(gap_counts),
           'missing_days':sum(map(len,gap_days.values())),'requested_days':requested,
           'requested_months':len(calendar),'gap_only_months':len(calendar-data_months),
           'largest_data_parquet':max(files[x] for x in files if x.startswith('.partitions/')),
           'allocation_bytes':187270569,'all_files_schemas_hashes_rows_raw_values_ordinals_gaps_verified':True}
print(json.dumps(summary,sort_keys=True),flush=True)
```

### Script 2: `cex002_reviewer_comparisons.py`

SHA-256: `936762a58912533e6077b2bbc745250120d80a7cbf07838dde3cae4d7d296beb`
Path: `/tmp/cex002_reviewer_comparisons.py`

```python
import hashlib,json
from pathlib import Path
from decimal import Decimal
from fractions import Fraction
from datetime import datetime,timezone
import pyarrow.parquet as pq

root=Path('data/.cex002_liquidation_observed_daily')
def read(p,digest):
    assert p.is_file() and not p.is_symlink(),p
    body=p.read_bytes()
    assert hashlib.sha256(body).hexdigest()==digest,p
    return body
comp=json.loads(read(root/'.comparison/bd76dd2069e658ce11a00b7685e0008d4d5be0bec682acdf5640552a31af3391.json','bd76dd2069e658ce11a00b7685e0008d4d5be0bec682acdf5640552a31af3391'))
products={
 'price_close':('data/.cex002_bar_1h','3b803d3e84e5d0bf87064626cc0504e9ff92e225a53ba83cdd4e09c38a2e9fd7','open_time','close','/ohlcv-history'),
 'funding_rate':('data/.cex002_funding_realized','57628164f19d182164b6058d9e51f794430cc918706c088f430e1c01d2898522','calc_time','last_funding_rate','/funding-rate-history'),
 'open_interest':('data/.cex002_open_interest_5m','bb089fc992326c66ddb65cea03dda92e8cd9fcf7cb7f373821f04a16db9168e4','create_time','sum_open_interest','/open-interest-history')}
officials={}
for metric,(path,digest,tc,vc,ep) in products.items():
    r=Path(path)
    assert list((r/'.complete').glob('*.json'))==[r/'.complete'/f'{digest}.json']
    d=json.loads(read(r/'.complete'/f'{digest}.json',digest))
    officials[metric]={(p['native_symbol'],p['utc_month']):p for p in d['partitions']}
secondary={}
for rec in comp['overlap_receipts']:
    b=read(Path(rec['path']),rec['source_sha256'])
    assert len(b)==rec['byte_size']
    secondary[rec['endpoint']]={x['symbol']:x['history'] for x in json.loads(b,parse_float=Decimal)}
def f(doc):
    return Fraction(int(doc['numerator']),int(doc['denominator']))
seen=set(); results=[]; cache={}
for e in comp['entries']:
    symbol,day,metric=e['symbol'],e['utc_day'],e['metric']
    assert (symbol,day,metric) not in seen
    seen.add((symbol,day,metric))
    assert symbol in ('BTCUSDT','ETHUSDT') and day in ('2020-10-01','2020-11-15','2020-12-31')
    path,digest,tc,vc,endpoint=products[metric]
    start=int(datetime.fromisoformat(day).replace(tzinfo=timezone.utc).timestamp()*1000)
    history=secondary[endpoint][symbol+'_PERP.A']
    matches=[(i,h) for i,h in enumerate(history) if h['t']*1000==start]
    assert len(matches)==1
    ordinal,h=matches[0]
    assert e['secondary']['point_ordinal']==ordinal and e['secondary']['timestamp_s']==h['t']
    assert e['secondary']['endpoint']==endpoint and f(e['secondary']['value'])==Fraction(h['c'])
    rec=next(r for r in comp['overlap_receipts'] if r['endpoint']==endpoint)
    assert e['secondary']['source_sha256']==rec['source_sha256']
    desc=officials[metric].get((symbol,day[:7]))
    if desc is None:
        assert metric=='open_interest' and symbol=='ETHUSDT'
        assert e['status']=='official_overlap_unavailable' and e['official'] is None and e['difference'] is None
        assert min(m for s,m in officials[metric] if s==symbol)=='2021-12'
        results.append({'symbol':symbol,'day':day,'metric':metric,'status':e['status'],'secondary':str(h['c'])})
        continue
    key=(metric,symbol,day[:7])
    if key not in cache:
        r=Path(path)
        read(r/desc['parquet_path'],desc['parquet_sha256'])
        lineage=json.loads(read(r/desc['lineage_path'],desc['lineage_sha256']))
        assert lineage['parquet_sha256']==desc['parquet_sha256']
        rows=pq.ParquetFile(r/desc['parquet_path']).read().to_pylist()
        assert len(rows)==desc['row_count']
        cache[key]=(rows,lineage)
    rows,lineage=cache[key]
    same=[r for r in rows if start<=r[tc]<start+86400000]
    chosen=max(same,key=lambda r:r[tc]); o=e['official']
    assert o['completion_sha256']==digest
    for k in ('parquet_path','parquet_sha256','lineage_path','lineage_sha256'): assert o[k]==desc[k]
    assert o['timestamp_ms']==chosen[tc] and o['source_row_ordinal']==chosen['source_row_ordinal'] and o['raw_object_ref']==chosen['raw_object_ref']
    assert o['raw_source']==next(r for r in lineage['raw_objects'] if r['raw_object_ref']==chosen['raw_object_ref'])
    assert f(o['value'])==Fraction(chosen[vc])
    sv=Fraction(h['c'])/(100 if metric=='funding_rate' else 1)
    assert f(e['secondary_fractional_value'])==sv and f(e['difference'])==sv-Fraction(chosen[vc])
    result={'symbol':symbol,'day':day,'metric':metric,'secondary_fraction':str(sv),'official':str(chosen[vc]),'difference':str(f(e['difference'])),'official_timestamp_ms':chosen[tc],'secondary_ordinal':ordinal,'official_ordinal':chosen['source_row_ordinal'],'status':e['status']}
    if metric=='price_close':
        assert chosen[tc]==start+23*3600000 and chosen['close_time']==o['close_time_ms']==start+86400000-1
        assert e['status']=='exact_value_match' and f(e['difference'])==0
    elif metric=='funding_rate':
        assert chosen['funding_interval_hours']==o['funding_interval_hours']==8
        assert e['status']=='exact_value_match' and f(e['difference'])==0
    else:
        assert chosen[tc]==start+86400000-300000
        mn=min(Fraction(r[vc]) for r in same); mx=max(Fraction(r[vc]) for r in same)
        assert f(o['same_day_min'])==mn and f(o['same_day_max'])==mx
        assert e['status']=='measured_difference'
        result.update(same_day_min=str(mn),same_day_max=str(mx),secondary_within_daily_range=mn<=sv<=mx)
    results.append(result)
assert len(seen)==18
print(json.dumps({'independently_reconstructed_entries':len(results),'official_partitions_checked':len(cache),'results':results},indent=2))
```