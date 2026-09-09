# CEX-002 Record 479 - Cost Calibration Integration and Real Run Record

- **Date:** 2026-09-09
- **Actor:** Jr Dev — Hermes (`meituan/longcat-2.0:free`)
- **Ticket:** CEX-002
- **Gate 2:** `ACCEPTED`
- **Gate 3:** `IN_PROGRESS` — eight products accepted
- **Next required actor:** Lead Quantitative Finance Researcher/Engineer
- **Next ticket:** `NONE`

## Workflow summary

Hermes executed the complete Review 478 authorization: read-only preflight, the
four-step validation suite, exact three-path integration, capacity/authority
preproof, and one foreground local conversion. The run failed at the component
bounds check with exit 1. Execution stopped at the first nonzero command per
the first-nonzero rule. No source patch, retry, relaunch, output deletion or
diagnostic mutation was performed.

## Step 1 — Preflight proof

```
$ git rev-parse HEAD origin/main
8d18de6883c4d1696a3e597dd07a9744abb56b59
8d18de6883c4d1696a3e597dd07a9744abb56b59

$ git diff --cached --name-only
(empty output — empty index confirmed)

$ sha256sum src/cryptofactors/ingest/binance_usdm_cost_calibration.py scripts/research/normalize_binance_usdm_cost_calibration.py tests/ingest/test_binance_usdm_cost_calibration.py
2026982aa275ffb09e5dceb75453d0290cd7c0b35e248f48e45cf3f3cee3b41d  src/cryptofactors/ingest/binance_usdm_cost_calibration.py
196bbd5efec2465ca17a62b728eed754c85096c71409e8a35f47ba68a1b4162d  scripts/research/normalize_binance_usdm_cost_calibration.py
0aa2c218e7cdccaef37327dbf9c4f9229fc74744bae01d98ad50843781a5d701  tests/ingest/test_binance_usdm_cost_calibration.py

$ wc -l src/cryptofactors/ingest/binance_usdm_cost_calibration.py scripts/research/normalize_binance_usdm_cost_calibration.py tests/ingest/test_binance_usdm_cost_calibration.py
1551 src/cryptofactors/ingest/binance_usdm_cost_calibration.py
   57 scripts/research/normalize_binance_usdm_cost_calibration.py
  907 tests/ingest/test_binance_usdm_cost_calibration.py
```

HEAD == origin/main == `8d18de6883c4d1696a3e597dd07a9744abb56b59` (published review
commit). Empty index confirmed. All three file SHA-256 hashes and line counts
match Review 478's accepted table exactly.

## Step 2 — Validation suite

```
$ PYTHONPATH=src .venv/bin/python -m pytest tests/ingest/test_binance_usdm_cost_calibration.py -q --tb=short
......................................                                   [100%]
(exit 0 — 38 cases passed)

$ PYTHONPATH=src .venv/bin/python -m ruff check src/cryptofactors/ingest/binance_usdm_cost_calibration.py scripts/research/normalize_binance_usdm_cost_calibration.py tests/ingest/test_binance_usdm_cost_calibration.py
All checks passed!
(exit 0)

$ python3 scripts/check_repo_control.py
Repo control check: PASS
(exit 0)

$ git diff --check
(empty output — no whitespace errors)
(exit 0)
```

All four checks passed.

## Step 3 — Integration

Staged exactly the three accepted paths:

```
$ git add src/cryptofactors/ingest/binance_usdm_cost_calibration.py scripts/research/normalize_binance_usdm_cost_calibration.py tests/ingest/test_binance_usdm_cost_calibration.py
$ git diff --cached --name-only
scripts/research/normalize_binance_usdm_cost_calibration.py
src/cryptofactors/ingest/binance_usdm_cost_calibration.py
tests/ingest/test_binance_usdm_cost_calibration.py

$ git diff --cached --check
(empty output)
```

Committed and pushed:

```
[main e092d17] CEX-002: integrate corrected Batch C cost calibration source
 3 files changed, 2515 insertions(+)
 create mode 100644 scripts/research/normalize_binance_usdm_cost_calibration.py
 create mode 100644 src/cryptofactors/ingest/binance_usdm_cost_calibration.py
 create mode 100644 tests/ingest/test_binance_usdm_cost_calibration.py

$ git push
To github.com:larslarsen/Crypto-Multifactor-Bot.git
   8d18de6..e092d17  main -> main
```

Post-integration proof:

```
$ git rev-parse HEAD origin/main
e092d17afa3d229135d89fa144ddc2b120e8e2f7
e092d17afa3d229135d89fa144ddc2b120e8e2f7
```

HEAD == origin/main == `e092d17afa3d229135d89fa144ddc2b120e8e2f7`. The three source
hashes were reproved unchanged after integration.

## Step 4 — Capacity and authority preproof

Pinned authority hashes:

```
$ sha256sum research/sprint_004/62_CEX002_GATE1_SOURCE_PROCUREMENT.json research/sprint_004/258_CEX002_GATE2_STORAGE_SIZING_V3.json data/cex002_qualify/gate2_revision_candidate_v3/manifest/4dacaba97c17ad9c4a9724f5db74dfab7ee98760cdb3df6dea46ab37c0684c2d.json.gz
f27b2ba7e6eff3a8b1385d985c49ee64ef60a394737b1246130d0f37b9015f09  research/sprint_004/62_CEX002_GATE1_SOURCE_PROCUREMENT.json
3995a5072a7d84baecae677ceff6e1c7af9dd076daadec04a31717ffc8f16589  research/sprint_004/258_CEX002_GATE2_STORAGE_SIZING_V3.json
4dacaba97c17ad9c4a9724f5db74dfab7ee98760cdb3df6dea46ab37c0684c2d  data/cex002_qualify/gate2_revision_candidate_v3/manifest/4dacaba97c17ad9c4a9724f5db74dfab7ee98760cdb3df6dea46ab37c0684c2d.json.gz
```

All three match Review 478's pinned authorities.

Membership completion:

```
$ sha256sum data/.cex002_perpetual_membership/.complete/01d054b34c3a92cc349f9484296031e8cbb67ae7e62eb0a8b38c6d3928d977a3.json
01d054b34c3a92cc349f9484296031e8cbb67ae7e62eb0a8b38c6d3928d977a3  data/.cex002_perpetual_membership/.complete/01d054b34c3a92cc349f9484296031e8cbb67ae7e62eb0a8b38c6d3928d977a3.json
```

Membership completion hash matches Review 478 (`01d054b3...`).

PyArrow and writer identity:

```
$ PYTHONPATH=src .venv/bin/python -c "import pyarrow; print('pyarrow', pyarrow.__version__)"
pyarrow 25.0.0

$ PYTHONPATH=src .venv/bin/python -c "from cryptofactors.acquisition.binance_usdm_harmonic_sizing import writer_identity; print(writer_identity())"
pyarrow25.0.0_parquet2.6_zstdl3_rowgroup65536_nostats_typed_v2
```

PyArrow is exactly 25.0.0. Writer identity is
`pyarrow25.0.0_parquet2.6_zstdl3_rowgroup65536_nostats_typed_v2`, matching the
accepted contract.

Output and process state:

```
$ test -e data/.cex002_cost_calibration && echo "EXISTS" || echo "ABSENT"
ABSENT
$ test -L data/.cex002_cost_calibration && echo "SYMLINK" || echo "NOT_SYMLINK"
NOT_SYMLINK
$ pgrep -af normalize_binance_usdm_cost_calibration | grep -v pgrep | grep -v hermes || echo "NO_LIVE_NORMALIZER"
NO_LIVE_NORMALIZER
```

Output root absent (not a symlink). No live cost normalizer process.

Capacity:

```
$ PYTHONPATH=src .venv/bin/python -c "import os; st=os.statvfs('.'); print('available_bytes', st.f_bavail*st.f_frsize)"
available_bytes 192930070528
```

Pre-run available bytes: **192,930,070,528** (above the required 73,204,546,497).

## Step 5 — Foreground local conversion (failed)

UTC start: **2026-09-09T04:50:01Z**

```
$ PYTHONPATH=src .venv/bin/python scripts/research/normalize_binance_usdm_cost_calibration.py \
    --report research/sprint_004/62_CEX002_GATE1_SOURCE_PROCUREMENT.json \
    --sizing research/sprint_004/258_CEX002_GATE2_STORAGE_SIZING_V3.json \
    --generation0-state data/cex002_qualify/gate2/state.sqlite \
    --generation0-content-root data/cex002_qualify/gate2/content \
    --v3-manifest data/cex002_qualify/gate2_revision_candidate_v3/manifest/4dacaba97c17ad9c4a9724f5db74dfab7ee98760cdb3df6dea46ab37c0684c2d.json.gz \
    --recovery-root data/cex002_recovery \
    --membership-root data/.cex002_perpetual_membership \
    --output-root data/.cex002_cost_calibration
```

The run failed with exit 1 at `_enforce_component_bounds`:

```
Traceback (most recent call last):
  File "/home/lars/Crypto_Multifactor_Bot/scripts/research/normalize_binance_usdm_cost_calibration.py", line 57, in <module>
    raise SystemExit(main())
  File "/home/lars/Crypto_Multifactor_Bot/scripts/research/normalize_binance_usdm_cost_calibration.py", line 28, in main
    result = normalize_from_authorities(...)
  File "/home/lars/Crypto_Multifactor_Bot/src/cryptofactors/ingest/binance_usdm_cost_calibration.py", line 1551, in normalize_from_authorities
    return normalize_cost_sources(sources, memberships, gaps, output_root, enforce_full_corpus=True, hooks=hooks)
  File "/home/lars/Crypto_Multifactor_Bot/src/cryptofactors/ingest/binance_usdm_cost_calibration.py", line 1462, in normalize_cost_sources
    _enforce_component_bounds(published)
  File "/home/lars/Crypto_Multifactor_Bot/src/cryptofactors/ingest/binance_usdm_cost_calibration.py", line 1372, in _enforce_component_bounds
    _require(...)
  File "/home/lars/Crypto_Multifactor_Bot/src/cryptofactors/ingest/binance_usdm_cost_calibration.py", line 239, in _require
    raise CostCalibrationError(message)
cryptofactors.ingest.binance_usdm_cost_calibration.CostCalibrationError: retained_book_ticker measured allocation exceeded
```

UTC end: **2026-09-09T11:14:55Z**
Elapsed: **6h 24m 54s** (23,094 seconds)
Exit code: **1**

Post-run available bytes: **168,851,566,592** (captured separately from the
logical output byte sum).

## Step 6 — Read-only failure inventory (no completion claim)

Per the first-nonzero rule, execution stopped. No completion was published.
The partial output inventory below is read-only evidence, not a completion
claim.

### Partial output inventory

| Component | Partitions (parquet) | Lineage (json) | Rows | Parquet bytes | Max single partition bytes |
|---|---:|---:|---:|---:|---:|
| retained_book_ticker | 866 | 866 | 882,076,090 | 16,475,583,828 | 368,974,047 |
| retained_book_depth | 2,226 | 2,226 | 57,054,290 | 1,455,739,653 | 1,977,525 |
| fee_authority_gap | 771 | 771 | 771 | 2,634,470 | 3,428 |
| official_fee_schedule | 1 | 1 | 0 | 3,551 | 3,551 |
| scenario_policy | 1 | 1 | 2 | 3,651 | 3,651 |
| **Total** | **3,865** | **3,865** | **939,132,153** | **17,933,965,153** | — |

- Total parquet files: 3,865
- Total lineage JSON files: 3,865
- Total parquet bytes: 17,933,965,153
- Total lineage bytes: 6,679,783
- Completion file: **absent** (no `.complete` descriptor)
- Symlinks: **0**
- Staging files left: **0**
- Temporary files left: **0**

### Bound comparison (the failure)

The `COMPONENT_LIMITS` for `retained_book_ticker` (source lines 108–113):

| Field | Bound | Measured | Status |
|---|---:|---:|:---|
| partitions | 866 | 866 | OK |
| rows | 745,543,507 | 882,076,090 | **EXCEEDED** |
| bytes | 33,300,608,759 | 16,475,583,828 | OK |
| largest_partition_bytes | 644,623,616 | 368,974,047 | OK |

The `retained_book_ticker` row count **882,076,090 exceeds the bound
745,543,507 by 136,532,583 rows**. This is the failing assertion in
`_enforce_component_bounds` (source line 1374). All other components are within
their bounds.

### Other components within bounds

| Component | Bound rows | Measured rows | Bound bytes | Measured bytes | Status |
|---|---:|---:|---:|---:|:---|
| retained_book_depth | 213,335,188 | 57,054,290 | 4,654,218,130 | 1,455,739,653 | OK |
| fee_authority_gap | 771 | 771 | 2,642,988 | 2,634,470 | OK |
| official_fee_schedule | 0 | 0 | 3,551 | 3,551 | OK |
| scenario_policy | 2 | 2 | 3,651 | 3,651 | OK |

## Procedural failure preserved (Laguna session)

Record 479 preserves the procedural rejection of the closed Laguna session
`20260908_213716_d483b4` described in Review 478:

- At HEAD `d22f8302853a1584a83b4f72420ce8aa6abd1d3e`, Laguna used
  `git diff --quiet` to test the index, received exit 1 from the intentionally
  dirty working tree, and repeated that command despite the first-nonzero rule.
- It then compared Git blob SHA-1 from `git hash-object` with the accepted file
  SHA-256 and falsely reported a source mismatch.
- Its attempted nonexistent `shell` tool did not execute.
- All actual commands were read-only. Reviewer inspection confirmed the empty
  index, unchanged HEAD/origin and the accepted three file SHA-256 values.
- This was a procedural rejection, not a source defect.

Hermes's replacement session did not repeat these errors: it used
`git diff --cached --name-only` for the empty-index proof, `sha256sum` for file
identities, and `wc -l` for line counts.

## Limitations

- The run failed at the component bounds check; no completion descriptor was
  published. Product acceptance remains with the reviewer.
- The partial output inventory is read-only evidence gathered after the stop.
  It is not a completion claim and was not produced by the normalizer's own
  completion path.
- The cause of the ticker row excess (882,076,090 measured vs 745,543,507
  bound) is not diagnosed here. No source patch, retry or second invocation
  was authorized.
- No Batch D, catalog transaction, NautilusTrader, model, experiment or next
  ticket work was performed.
