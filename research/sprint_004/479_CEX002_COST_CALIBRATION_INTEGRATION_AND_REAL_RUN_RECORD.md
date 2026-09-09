# CEX-002 Record 479 - Cost Calibration Integration and Real Run Record

- **Date:** 2026-09-09
- **Actor:** Jr Dev — Hermes (`meituan/longcat-2.0:free`)
- **Ticket:** CEX-002
- **Gate 2:** `ACCEPTED`
- **Gate 3:** `IN_PROGRESS` — eight products accepted
- **Next required actor:** Lead Quantitative Finance Researcher/Engineer
- **Next ticket:** `NONE`

## Workflow summary

Hermes executed the complete Review 478 "Finalizer source acceptance and current Hermes workflow" authorization: preflight proof, the four-step validation suite, exact three-path finalizer integration, capacity/authority preproof with preserved-inventory hashing, one foreground preserved-output finalization, full post-run verification and reconciliation, one authorized deterministic replay, and this in-place Record 479 update. The sole foreground finalization succeeded with `completion_reused=false`, 3,865 partitions and 939,130,319 source rows. The replay confirmed byte-identical completion reuse with the entire preserved inventory unchanged.

## Step 1 — Preflight proof

```
$ git rev-parse HEAD origin/main
a20ad200d211a0c312bd661707d6c3eff3d6a3e2
a20ad200d211a0c312bd661707d6c3eff3d6a3e2

$ git diff --cached --name-only
(empty output — empty index confirmed)

$ sha256sum src/cryptofactors/ingest/binance_usdm_cost_finalization.py scripts/research/finalize_binance_usdm_cost_calibration.py tests/ingest/test_binance_usdm_cost_finalization.py
b9dda86e6e0bbe046bec05ba402aca0c642e102114b5e737d4dc2ad92d010528  src/cryptofactors/ingest/binance_usdm_cost_finalization.py
6e9609c4fa781c32e2044e31338e0d03f68f401cc0445f8e8bd5c09b30bcdf18  scripts/research/finalize_binance_usdm_cost_calibration.py
51f3ce4b4d4fa6e764558ee2f86b22a8e8bbb9f94065173333a20ad31161cc1f  tests/ingest/test_binance_usdm_cost_finalization.py

$ wc -l src/cryptofactors/ingest/binance_usdm_cost_finalization.py scripts/research/finalize_binance_usdm_cost_calibration.py tests/ingest/test_binance_usdm_cost_finalization.py
  867 src/cryptofactors/ingest/binance_usdm_cost_finalization.py
   55 scripts/research/finalize_binance_usdm_cost_calibration.py
  592 tests/ingest/test_binance_usdm_cost_finalization.py
```

HEAD == origin/main == `a20ad200d211a0c312bd661707d6c3eff3d6a3e2` (published Review 478
commit). Empty index confirmed. All three file SHA-256 hashes and line counts
match Review 478's accepted table exactly.

## Step 2 — Validation suite

```
$ PYTHONPATH=src .venv/bin/python -m pytest tests/ingest/test_binance_usdm_cost_finalization.py -q --tb=short
..............................                                           [100%]
(exit 0 — 30 cases passed)

$ PYTHONPATH=src .venv/bin/python -m ruff check src/cryptofactors/ingest/binance_usdm_cost_finalization.py scripts/research/finalize_binance_usdm_cost_calibration.py tests/ingest/test_binance_usdm_cost_finalization.py
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
$ git add src/cryptofactors/ingest/binance_usdm_cost_finalization.py scripts/research/finalize_binance_usdm_cost_calibration.py tests/ingest/test_binance_usdm_cost_finalization.py
$ git diff --cached --name-only
scripts/research/finalize_binance_usdm_cost_calibration.py
src/cryptofactors/ingest/binance_usdm_cost_finalization.py
tests/ingest/test_binance_usdm_cost_finalization.py

$ git diff --cached --check
(empty output)
```

Committed and pushed:

```
[main ab671b4] CEX-002: integrate cost calibration finalizer source drop
 3 files changed, 1514 insertions(+)
 create mode 100644 scripts/research/finalize_binance_usdm_cost_calibration.py
 create mode 100644 src/cryptofactors/ingest/binance_usdm_cost_finalization.py
 create mode 100644 tests/ingest/test_binance_usdm_cost_finalization.py

$ git push
To github.com:larslarsen/Crypto-Multifactor-Bot.git
   a20ad20..ab671b4  main -> main
```

Post-integration proof:

```
$ git rev-parse HEAD origin/main
ab671b4713add0d9367c08cb18603f99b037fe1a
ab671b4713add0d9367c08cb18603f99b037fe1a
```

HEAD == origin/main == `ab671b4713add0d9367c08cb18603f99b037fe1a`. The three source
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

Generation-0 seal head inside `data/cex002_qualify/gate2/state.sqlite`
(`seal_head` table): `8875338d0a2b7984fb8fefd7a716a04486667cfb1d726c3758f5496f065ef7ab`
(matches Review 478's pinned generation-0 seal).

Original producer SHA:

```
$ sha256sum src/cryptofactors/ingest/binance_usdm_cost_calibration.py
2026982aa275ffb09e5dceb75453d0290cd7c0b35e248f48e45cf3f3cee3b41d  src/cryptofactors/ingest/binance_usdm_cost_calibration.py
```

Matches Review 478's original producer hash.

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

$ PYTHONPATH=src .venv/bin/python -c "from cryptofactors.ingest.binance_usdm_cost_calibration import writer_identity; print(writer_identity())"
pyarrow25.0.0_parquet2.6_zstdl3_rowgroup65536_nostats_typed_v2
```

PyArrow is exactly 25.0.0. Writer identity is
`pyarrow25.0.0_parquet2.6_zstdl3_rowgroup65536_nostats_typed_v2`, matching the
accepted contract.

Preserved root safety:

```
$ test -L data/.cex002_cost_calibration && echo "SYMLINK" || echo "NOT_SYMLINK"
NOT_SYMLINK
$ test -e data/.cex002_cost_calibration/.complete && echo "COMPLETE_EXISTS" || echo "NO_COMPLETE"
NO_COMPLETE
$ find data/.cex002_cost_calibration/ -type l | wc -l
0
$ pgrep -af 'cost_calibration|cost_finalization' | grep -v pgrep | grep -v hermes || echo "NO_LIVE_PROCESS"
NO_LIVE_PROCESS
```

Preserved root is a real directory (not a symlink), no completion exists,
zero symlinks, no live cost normalizer/finalizer process.

Preserved inventory (exact Review 478 encoding: UTF-8
`json.dumps(entries, sort_keys=True, separators=(',', ':'))` no newline;
entries `{path, sha256, bytes}` sorted by path):

```
file_count=7731
total_bytes=17940823719
digest=482cda93ba68c93d46a17207bbb6b01764dd5b66d72d936860eba67d2f399b98
```

Matches Review 478's pinned inventory digest exactly. Inode/mtime/hash facts
for all 7,731 files captured to `/tmp/cex002_cost_prefacts.jsonl` for
post-run comparison.

Capacity:

```
$ PYTHONPATH=src .venv/bin/python -c "import os; st=os.statvfs('data/.cex002_cost_calibration'); print('available_bytes', st.f_bavail*st.f_frsize)"
available_bytes 155803348992
```

Pre-run available bytes: **155,803,348,992** (above the required
73,204,546,497 floor).

## Step 5 — Foreground local finalization (success)

UTC start: **2026-09-09T17:53:12+00:00** (observed pre-command)

```
$ TERMINAL_MAX_FOREGROUND_TIMEOUT=43200 PYTHONPATH=src .venv/bin/python scripts/research/finalize_binance_usdm_cost_calibration.py \
    --report research/sprint_004/62_CEX002_GATE1_SOURCE_PROCUREMENT.json \
    --sizing research/sprint_004/258_CEX002_GATE2_STORAGE_SIZING_V3.json \
    --generation0-state data/cex002_qualify/gate2/state.sqlite \
    --generation0-content-root data/cex002_qualify/gate2/content \
    --v3-manifest data/cex002_qualify/gate2_revision_candidate_v3/manifest/4dacaba97c17ad9c4a9724f5db74dfab7ee98760cdb3df6dea46ab37c0684c2d.json.gz \
    --recovery-root data/cex002_recovery \
    --membership-root data/.cex002_perpetual_membership \
    --output-root data/.cex002_cost_calibration
```

The finalizer exited 0. Exact terminal output:

```json
{"completion_path":"/home/lars/Crypto_Multifactor_Bot/data/.cex002_cost_calibration/.complete/fa4eced65e03e548cf5bf6500a9674a192a70dde9edf12d49c1f8bd539ad6f9e.json","completion_reused":false,"completion_sha256":"fa4eced65e03e548cf5bf6500a9674a192a70dde9edf12d49c1f8bd539ad6f9e","partition_count":3865,"source_rows":939130319}
```

UTC end: **2026-09-09T18:00:47+00:00** (observed post-command)
Elapsed: **7 minutes 35 seconds** (455 seconds wall)
Exit code: **0**

Post-run available bytes: **155,384,172,544** (captured separately from the
logical output byte sum).

Key reported facts:
- `completion_reused`: **false** (first-time finalization)
- `partition_count`: **3,865**
- `source_rows`: **939,130,319**
- `completion_sha256`: `fa4eced65e03e548cf5bf6500a9674a192a70dde9edf12d49c1f8bd539ad6f9e`

## Step 6 — Post-run verification and reconciliation

Post-run tree inventory:

```
file_count=7732
total_bytes=17943795556
digest=90aaa5ae434dc1eaf9ef7aebc0d86c0af594fcf9edfb052d99a8ee80bbcab5f9
```

Exactly 7,732 files (7,731 preserved + 1 completion). Empty staging. Zero
symlinks. All 7,731 preserved files retain identical inode/mtime/hash — no
preserved artifact was mutated.

Completion descriptor verified at
`.complete/fa4eced65e03e548cf5bf6500a9674a192a70dde9edf12d49c1f8bd539ad6f9e.json`:

### Ticker row projection disposition

```json
{
  "actual_rows": 882076090,
  "excess_rows": 136532583,
  "ordinary_sizing_check_passed": false,
  "projected_rows": 745543507,
  "status": "EXCEEDED_REVIEWED_EXACT_ARTIFACT_VARIANCE"
}
```

`ordinary_sizing_check_passed` is **false** — the exceeded ticker projection
is preserved explicitly, never relabeled a passed sizing check.

### Component rows

| Component | Rows |
|---:|---:|
| retained_book_ticker | 882,076,090 |
| retained_book_depth | 57,054,229 |
| fee_authority_gap | 771 |
| official_fee_schedule | 0 |
| scenario_policy | 2 |
| **Total** | **939,131,092** |

Book rows total 939,130,319; all component rows total 939,131,092.

### Component measured facts

| Component | Partitions | Parquet bytes | Largest file bytes |
|---|---:|---:|---:|
| retained_book_ticker | 866 | 16,475,583,828 | 368,974,047 |
| retained_book_depth | 2,226 | 1,455,739,653 | 1,977,525 |
| fee_authority_gap | 771 | 2,634,470 | 3,428 |
| official_fee_schedule | 1 | 3,551 | 3,551 |
| scenario_policy | 1 | 3,651 | 3,651 |

Parquet bytes total 17,933,965,153 (matches Review 478).

### Quote states

```json
{"ask_only": 76, "bid_only": 279, "empty": 17, "two_sided": 882075718}
```

Sum = 882,075,718 + 279 + 76 + 17 = 882,076,090 (matches ticker rows).
Matches Review 478's reviewer-audited quote-state counts.

### Source equation

```json
{"compressed_bytes": 12522974218, "deduplicated_rows": 0, "dropped_rows": 0,
 "generation0_objects": 2790, "objects": 3144, "physical_rows": 939130319,
 "recovery_objects": 354, "retained_rows": 939130319}
```

3,144 objects (2,790 generation-0 + 354 recovery), 12,522,974,218 compressed
bytes, zero deduplicated/dropped rows. Matches Review 478.

### Measured output bytes

```json
{"completion": 2971837, "lineage": 6679783, "parquet": 17933965153,
 "source_gaps": 178783, "total": 17943795556}
```

Logical output total: **17,943,795,556** bytes. The preserved-inventory bytes
(17,940,823,719) plus completion (2,971,837) = 17,943,795,556. All byte
limits including completion are satisfied.

### Fee authority

```json
{"gap_kind": "historical_fee_schedule_unavailable", "gap_rows": 771,
 "missing_fee_is_zero": false, "official_historical_rows": 0}
```

Exactly 771 fee-gap identities, zero official historical rows. Matches
Review 478.

### Scenario policy

```json
{"authority_class": "ASSUMED_CONSERVATIVE", "charges_each_side": true,
 "historical_observation": false, "historical_upper_bound": false,
 "policy_known_at": "2026-08-23T03:00:00Z", "rows": 2}
```

Two immutable policy rows, not historical observations. Matches Review 478.

### Frozen source gaps

```json
{"bytes": 178783, "path": ".source-gaps/aace941a43e38c2f790fed4c383e08cbbd27d3f5f7215bc95b50bb134ae3519e.json",
 "row_count": 494, "sha256": "aace941a43e38c2f790fed4c383e08cbbd27d3f5f7215bc95b50bb134ae3519e"}
```

494-row source-gap JSON at the pinned SHA-256. Matches Review 478.

### Preserved inventory binding

```json
{"bytes": 17940823719, "directories": 11386, "files": 7731,
 "sha256": "482cda93ba68c93d46a17207bbb6b01764dd5b66d72d936860eba67d2f399b98"}
```

Matches Review 478's pinned inventory digest exactly.

### Authority binding

```json
{"cost_manifest": "04842ff6b9b58280b3ec2ea2644b3d44769be62d460bef785262cd4dd65cac57",
 "generation0_seal": "8875338d0a2b7984fb8fefd7a716a04486667cfb1d726c3758f5496f065ef7ab",
 "membership_completion": "01d054b34c3a92cc349f9484296031e8cbb67ae7e62eb0a8b38c6d3928d977a3",
 "report": "f27b2ba7e6eff3a8b1385d985c49ee64ef60a394737b1246130d0f37b9015f09",
 "sizing": "3995a5072a7d84baecae677ceff6e1c7af9dd076daadec04a31717ffc8f16589",
 "v3_manifest": "4dacaba97c17ad9c4a9724f5db74dfab7ee98760cdb3df6dea46ab37c0684c2d"}
```

All six authority hashes match Review 478's pinned values exactly.

### Code/config identity binding

- `normalizer_source_sha256`: `2026982aa275ffb09e5dceb75453d0290cd7c0b35e248f48e45cf3f3cee3b41d` (original producer)
- `finalizer_source_sha256`: `b9dda86e6e0bbe046bec05ba402aca0c642e102114b5e737d4dc2ad92d010528` (finalizer)
- `normalizer_integration_commit`: `e092d17afa3d229135d89fa144ddc2b120e8e2f7`
- `preserved_inventory_sha256`: `482cda93ba68c93d46a17207bbb6b01764dd5b66d72d936860eba67d2f399b98`
- `writer_identity`: `pyarrow25.0.0_parquet2.6_zstdl3_rowgroup65536_nostats_typed_v2`
- `schema_sha256`: `529b7ae46df4ba080daffbdf87f83f2a2abb179e5bbfdbc28af9f050a0d27069`
- `source_row_facts_sha256`: `aac31786a8f18088481cd00579c30dece80cf9907c792638d2e0047c076fc89b`

The `source_row_facts_sha256` matches Review 478's independently measured
per-source row-facts digest exactly.

## Step 7 — Deterministic replay proof

UTC start: **2026-09-09T18:03:40+00:00** (observed pre-command)

The same exact finalizer command (Step 5) was invoked once more with the
same `timeout=7200` and `TERMINAL_MAX_FOREGROUND_TIMEOUT=43200` as the
ticket's explicit deterministic replay proof. The run exited 0. Exact
terminal output:

```json
{"completion_path":"/home/lars/Crypto_Multifactor_Bot/data/.cex002_cost_calibration/.complete/fa4eced65e03e548cf5bf6500a9674a192a70dde9edf12d49c1f8bd539ad6f9e.json","completion_reused":true,"completion_sha256":"fa4eced65e03e548cf5bf6500a9674a192a70dde9edf12d49c1f8bd539ad6f9e","partition_count":3865,"source_rows":939130319}
```

UTC end: **2026-09-09T18:10:20+00:00** (observed post-command)
Elapsed: **6 minutes 40 seconds** (400 seconds wall)
Exit code: **0**

Key reported facts:
- `completion_reused`: **true** (byte-identical completion reused)
- `completion_sha256`: `fa4eced65e03e548cf5bf6500a9674a192a70dde9edf12d49c1f8bd539ad6f9e` (identical)
- `partition_count`: 3,865 (identical)
- `source_rows`: 939,130,319 (identical)

Post-replay tree inventory: 7,732 files, 17,943,795,556 bytes, digest
`90aaa5ae434dc1eaf9ef7aebc0d86c0af594fcf9edfb052d99a8ee80bbcab5f9`
— identical to post-run. All 7,731 preserved files retain identical
inode/mtime/hash. Only one completion exists (no duplicate).

## Original failed conversion history (preserved)

The original producer conversion remains recorded here as history. Its
row totals are corrected below per Review 478.

UTC start (workflow observation): **2026-09-09T04:50:01Z**
UTC end (workflow observation): **2026-09-09T11:14:55Z**

Review 478 distinguishes these workflow observation times from the exact
tool-call interval recorded by session evidence: **2026-09-09T04:52:20.233206Z**
to **2026-09-09T11:14:30.406978Z** (6h 22m 10.174s tool-call interval). The
observed endpoints include pre/post-command delay and are not the process
interval.

The run failed with exit 1 at `_enforce_component_bounds`:

```
cryptofactors.ingest.binance_usdm_cost_calibration.CostCalibrationError: retained_book_ticker measured allocation exceeded
```

Exit code: **1**

Post-run available bytes: **168,851,566,592** (the later observed capacity
per Review 478).

### Corrected partial output inventory

Review 478 corrects Record 479's row totals: the depth row count was 61 too
high and the total was 1,061 too high. Corrected values:

| Component | Partitions (parquet) | Lineage (json) | Rows | Parquet bytes | Max single partition bytes |
|---|---:|---:|---:|---:|---:|
| retained_book_ticker | 866 | 866 | 882,076,090 | 16,475,583,828 | 368,974,047 |
| retained_book_depth | 2,226 | 2,226 | 57,054,229 | 1,455,739,653 | 1,977,525 |
| fee_authority_gap | 771 | 771 | 771 | 2,634,470 | 3,428 |
| official_fee_schedule | 1 | 1 | 0 | 3,551 | 3,551 |
| scenario_policy | 1 | 1 | 2 | 3,651 | 3,651 |
| **Total** | **3,865** | **3,865** | **939,131,092** | **17,933,965,153** | — |

### Corrected bound comparison

| Field | Bound | Measured | Status |
|---|---:|---:|:---:|
| partitions | 866 | 866 | OK |
| rows | 745,543,507 | 882,076,090 | **EXCEEDED** |
| bytes | 33,300,608,759 | 16,475,583,828 | OK |
| largest_partition_bytes | 644,623,616 | 368,974,047 | OK |

### Other components within bounds (corrected depth)

| Component | Bound rows | Measured rows | Bound bytes | Measured bytes | Status |
|---|---:|---:|---:|---:|:---:|
| retained_book_depth | 213,335,188 | 57,054,229 | 4,654,218,130 | 1,455,739,653 | OK |
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

- The original producer conversion failed at the component bounds check; the
  preserved-output finalization succeeded under Review 478's exact-artifact
  variance. Product acceptance remains with the reviewer.
- The ticker row excess (882,076,090 measured vs 745,543,507 bound) is an
  underestimated row projection, not duplicated output (per Review 478's
  complete raw-count and encoded-ordinal audits). It remains explicit with
  `ordinary_sizing_check_passed: false`.
- Reviewer audits (`/tmp/cex002_cost_reviewer_audit.py`,
  `/tmp/cex002_cost_reviewer_raw_counts.py`,
  `/tmp/cex002_cost_reviewer_ordinals.py`) are cited as reviewer evidence,
  not as Hermes-executed checks.
- No Batch D, catalog transaction, NautilusTrader, model, experiment or next
  ticket work was performed.

## Temporary evidence helpers

Hermes authored these read-only temporary helpers as implementation evidence.
They are not production/test code and are not integrated:

- `/tmp/cex002_cost_hermes_inventory.py` — preserved-tree inventory using the
  exact Review 478 encoding.
- `/tmp/cex002_cost_hermes_prefacts.py` — captures pre-run inode/mtime/hash
  facts for post-run comparison.
- `/tmp/cex002_cost_hermes_postverify.py` — post-run tree inventory,
  completion identification, and preserved-file comparison.
- `/tmp/cex002_cost_hermes_read_completion.py` — reads and prints completion
  descriptor sections for verification.
