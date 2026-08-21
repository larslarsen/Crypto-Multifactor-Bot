# CEX-002 Ruff Integration and Corrected Candidate

Date: 2026-08-21
Author: Jr Dev - Hermes
Governing review: `research/sprint_004/133_CEX002_RUFF_SOURCE_ACCEPTANCE.md` (source) and `research/sprint_004/130_CEX002_SPARK_TEST_SOURCE_ACCEPTANCE.md` (test correction).
Integration base: `fee34a1010beddcc27166282af9c7f5cde139dba` (review-130 publication); review-130 reviewer publication is `247fcc1`.

## 1. Environment

- `HEAD == origin/main == d428aecf20e92528f16905efce9fb75ae9ea4e68` (after both Hermes integration commits e0068e7 and d428aec; pushed; origin/main = d428aec).
- No candidate process running (ps scan: none) before launch.
- Monolith preserved to `data/cex002_qualify/evidence/prior_reports/sha256/46d1980ecf384874e45c4c31f142c16efc5472ef63231e9456e264f3e94ef691.json` (1,059,297,547 B, SHA-256 `46d1980e...`), re-proved.
- 17 CEX fixtures intact.

## 2. Integration commits

### 2a. Source integration (review 133) — commit `e0068e7`

Hermes established HEAD == origin/main == `247fcc1` (review-133 reviewer publication) and re-hashed the two accepted paths, the three frozen paths, the 17 fixtures, and the monolith - all matched review 133 (no mismatch). Hermes staged exactly the two accepted paths.

| Path | Accepted SHA-256 (review 133) | vs HEAD |
|---|---|---|
| `src/cryptofactors/acquisition/binance_usdm_harmonic_qualification.py` | `8b006ad3eebf059f9d3ce4f3e75b22192bff1272c693b1a69931a3936c571b99` | differs -> staged |
| `tests/acquisition/test_binance_usdm_harmonic_qualification.py` | `500882b5fc784722bab9e69038ee0d28fbe22c6d8558237a46607e354e0c9463` | differs -> staged |

Frozen paths (review 133 accepted unchanged), verified identical to HEAD and not staged:

| Path | SHA-256 | Status |
|---|---|---|
| `scripts/research/qualify_binance_usdm_harmonic_sources.py` | `b4e9235406be5276619b4a69017ddb87a8cffefb691c2673f2e3b875cc775d96` | identical to HEAD (frozen) |
| `src/source_audit/download.py` | `f231930f743f4b2f415dd84a96ec3c1ec3b1c1efab5deb7536db57fce5473fa5` | identical to HEAD (frozen) |
| `tests/test_download_atomicity.py` | `30388dba0568912b7bbe3f83c5454de89cd8cf5cd1288f260d30cfda0bd8d587` | identical to HEAD (frozen) |

```
commit e0068e73192659ac3870aceeb03e2d2caa3402e7 (HEAD -> main, origin/main)
Author: Jr Dev - Hermes
    CEX-002: integrate review-133 Ruff corrections (src 8b006ad3 + test 500882b5)
2 files changed, 4 insertions(+), 3 deletions(-)
```

### 2b. Test correction integration (review 130) — commit `d428aec`

Hermes staged exactly `tests/acquisition/test_binance_usdm_harmonic_qualification.py` (the Spark-corrected test). Working-tree hash = review-133 accepted test hash `500882b5fc784722bab9e69038ee0d28fbe22c6d8558237a46607e354e0c9463` (Spark's correction, accepted by review 130).

```
commit d428aecf20e92528f16905efce9fb75ae9ea4e68 (HEAD -> main, origin/main)
Author: Jr Dev - Hermes
    CEX-002: integrate review-130 corrected CEX test source (Spark test correction)
1 file changed, 37 insertions(+), 6 deletions(-)
```

HEAD == origin/main == `d428aec`, index empty. No reset/restore/checkout/stash/clean/worktree-rewrite used; the monolith, ignored data, database sidecars, and every unrelated dirty path were not staged or touched. Hermes did not edit the accepted source or test; both ruff defects had already been closed by Spark's accepted correction before Hermes ran C3.

## 3. Focused commands (review-130 sequence restart)

Run in order; review 133: any nonzero exit stops the remaining commands and the candidate.

1. `.venv/bin/python -m pytest tests/acquisition/test_binance_usdm_harmonic_qualification.py -q --tb=short`
   - Exit: 0. Result: 256 passed, 0 failed (256 collected; 209 unique test functions). The two record-127 failures are resolved.
2. `.venv/bin/python -m pytest tests/test_download_atomicity.py -q --tb=short`
   - Exit: 0. Result: 18 passed (18 collected).
3. `.venv/bin/python -m ruff check src/cryptofactors/acquisition/binance_usdm_harmonic_qualification.py scripts/research/qualify_binance_usdm_harmonic_sources.py src/source_audit/download.py tests/acquisition/test_binance_usdm_harmonic_qualification.py tests/test_download_atomicity.py`
   - Exit: 0. `All checks passed!` (F402/F841 from record 131 resolved.)
4. `python3 scripts/check_repo_control.py`
   - Exit: 0. `Repo control check: PASS`.
5. `git show --check --oneline --no-renames HEAD`
   - Exit: 0. `d428aec CEX-002: integrate review-130 corrected CEX test source ...` (no whitespace violations).

All five focused commands passed. Sequence proceeds: monolith preservation (completed in section 4) -> candidate resume (section 6).

## 4. Monolith preservation

Before launch, Hermes atomically preserved the source monolith (never hard-linked) to the content address:

- Source: `research/sprint_004/62_CEX002_GATE1_SOURCE_PROCUREMENT.json` - SHA-256 `46d1980ecf384874e45c4c31f142c16efc5472ef63231e9456e264f3e94ef691`, 1,059,297,547 B (matches review 133 accepted monolith identity).
- Destination: `data/cex002_qualify/evidence/prior_reports/sha256/46d1980ecf384874e45c4c31f142c16efc5472ef63231e9456e264f3e94ef691.json`.
- Procedure: wrote a collision-safe sibling temp via `cp --reflink=always` (reflink unsupported -> regular cp), re-hashed and byte-measured the temp, required temp hash == accepted `46d1980e...` and size == 1,059,297,547, then mv-renamed to the content address, then re-hashed the final destination (post-rename reprove = `46d1980e...` / 1,059,297,547 B).
- The preserved artifact lives in the git-ignored data store and is never staged.

## 5. Before snapshot (pre-candidate)

Captured 2026-08-21T20:50:36Z. Immutable invariants verified against review 121/126 terminal state:

| Invariant (review 121 terminal) | Before | Match |
|---|---|---|
| plan_lock SHA-256 `e04a5ce2...` | `e04a5ce2...` | yes |
| budget_ledger SHA-256 `47341a9c...` | `47341a9c...` | yes |
| amendment_ledger exists | False | yes |
| retained raw tree digest `41cade46c...` | `41cade46c...` | yes |
| retained raw tree count / bytes | 186 / 1,015,198,547 | yes |
| listing entries count | 40,771 | yes (review 133 precondition) |
| listing unclaimed | 0 | yes |
| monolith preserved hash+size | `46d1980e...` / 1,059,297,547 | yes |

Candidate preconditions satisfied before launch: no candidate running; listing checkpoint at the required 40,771 entries / 0 unclaimed.

## 6. One corrected candidate-only execution

`.env` loaded only into the process environment (never printed; never in argv). Single bounded foreground invocation (50-min timeout, SIGTERM + 60s kill-after). Start 2026-08-21T13:51:14-07:00, end 2026-08-21T14:00:08-07:00, elapsed 534 s.

```bash
set -a
. ./.env
set +a
timeout --signal=TERM --kill-after=60s 50m .venv/bin/python scripts/research/qualify_binance_usdm_harmonic_sources.py --store-root data/cex002_qualify --progress-path data/cex002_qualify/cex002_qualification_progress.json --report-path research/sprint_004/62_CEX002_GATE1_SOURCE_PROCUREMENT.json --candidate-plan-only
candidate_status=$?
```

candidate_status = 2 - terminal evidence (review 133: Status 0 or 2 is terminal). One invocation only; no automatic second run.

Essential console output (verbatim; long lines folded for readability):

```
listing checkpoint bootstrap: claimed=0 checksum_blobs=186 skipped_already_bound=40771 unclaimed=0
Qualification report written to research/sprint_004/62_CEX002_GATE1_SOURCE_PROCUREMENT.json
manifest_detail: path=evidence/manifests/sha256/d9be584d7a1eecd43482ea1a05a0d9dd8cd681970c4ec5ff225740a28f27a5bf.jsonl.gz
  uncompressed_sha256=d9be584d7a1eecd43482ea1a05a0d9dd8cd681970c4ec5ff225740a28f27a5bf
  uncompressed_bytes=466717014
  compressed_sha256=8abf72fa22c6714051c2b451bfd27e17b6c84a65b7e476be63bc21f09f265945
  compressed_bytes=11288256
  records={'row': 733203, 'collision': 0, 'rejection': 0, 'raw_validation_pending_key': 733191, 'total_records': 1466395}
  reused_existing=false
gate_status=BLOCKED accepted=False symbols=1004
  blocked=['binance_usdm_perpetual_membership', 'binance_usdm_bar_1h', 'binance_usdm_open_interest_5m',
           'binance_usdm_funding_realized', 'binance_usdm_funding_indicative_1h',
           'binance_usdm_mark_index_basis_1h', 'binance_usdm_cost_calibration']
sample_plan: planned_new_bytes=0 budget=268435456 retained_bytes=805792081 budget_blocked=46
plan_lock: version=2 state=locked plan_digest=d6eb52ff73711df669e9388d06a6abca92cb61cc86a17169b7ed62f369f132c1 superseded=[0, 1]
budget: charged=0 spent_range=[0,1015198547] remaining=0 reserved=0
  legacy_state=legacy_budget_accounting_unresolved breach_state=unresolved
membership: basis=confirmed_perpetual_membership confirmed=771 unresolved=63
  classes={'confirmed_perpetual': 771, 'dated_delivery_candidate': 46, 'delivery_non_perpetual': 4,
           'settlement_artifact_candidate': 17, 'tradifi_perpetual': 170}
gate2_storage: state=unknown selected_raw_bytes=7833966625 cost_sample_bytes=12522974218
  projected_new_bytes=20352428237 available_bytes=173609000960 total_required_bytes=None
  unknown_components=['normalized_catalog_bytes', 'temporary_high_water_bytes', 'operating_reserve_bytes']
candidate_plan: state=candidate_unmigrated version=3 prior_version=2 plan_digest=0a1c358c8fee3df35d1049424502b11e38c0084592a03ab6f9de99b8a0078593
  envelope_digest=a14018c27d8e00d3f59d4181d7da546ca99d43f5625c34d39cb07398859605c3
  migration_authorized=False download_authorized=False
holdout: id=c842f813839e1dda375b351da0f693c54bcf932e33eb6e3394aba860c12346e2
  boundary_utc=2026-08-21T16:19:08.994166+00:00 stream_collector=False
listing_checkpoint: reused=39812 fetched=0 unclaimed=0 serializations=1 | workers=8 clients=1/1 retries=0
ERROR: incomplete product matrix is refused | context={'gate_status': 'BLOCKED', 'blocked_products': [ ... 7 products ...]}
CANDIDATE_STATUS=2
CANDIDATE_END=2026-08-21T14:00:08-07:00
```

## 7. After snapshot and delta proof

After snapshot captured 2026-08-21T21:03:06Z (immediate repeat of before snapshot).

### Immutable invariants proved unchanged (match review 121/126 terminal state)

| Field | Before | After | Unchanged |
|---|---|---|---|
| plan_lock SHA-256 `e04a5ce2...` | `e04a5ce2...` | `e04a5ce2...` | yes |
| budget_ledger SHA-256 `47341a9c...` | `47341a9c...` | `47341a9c...` | yes |
| amendment_ledger exists | False | False | yes |
| raw tree digest `41cade46c...` | `41cade46c...` | `41cade46c...` | yes |
| raw tree count / bytes | 186 / 1,015,198,547 | 186 / 1,015,198,547 | yes |
| listing unclaimed | 0 | 0 | yes |
| listing entries count | 40,771 | 40,771 | yes |
| listing_checkpoint SHA-256 `d584e22a...` | `d584e22a...` | `d584e22a...` | yes (reused=39,812, fetched=0) |
| monolith preserved hash+size | `46d1980e...` / 1,059,297,547 | `46d1980e...` / 1,059,297,547 | yes |

### Evolved-by-candidate deltas (expected; candidate-process authorized)

| Field | Before | After | Delta |
|---|---|---|---|
| report 62 on-disk SHA-256 | `46d1980e...` (1.06 GB monolith) | `e51ef2735c4937cf61cc614836478ee053c89f8100d5e4193a22e665f651fcd9` | compact replacement: 17,349,108 B |
| report 62 bytes | 1,059,297,547 | 17,349,108 | -1,041,948,439 (scalable writer) |
| retry_journal SHA-256 `ff4edb03...` | `ff4edb03...` | `ff4edb03...` | unchanged (retries=0) |
| progress SHA-256 | `332f2d87...` | `5c85bbf0...` | changed (candidate advance) |
| list_cache count / bytes | 40,961 / 5,158,272,575 | 40,961 / 5,158,272,575 | unchanged (fetched=0) |
| fapi_cache count / bytes | 9 / 8,619,549 | 10 / 9,697,128 | +1 / +1,077,579 (minor bootstrap) |
| coinalyze_cache count / bytes | 7 / 3,144,369 | 7 / 3,144,369 | unchanged |
| fs available bytes | 173,778,001,920 | 174,616,170,496 | +838,168,576 (report shrank 1.04 GB) |

### New artifacts created by the verified candidate (git-ignored data store)

- `data/cex002_qualify/evidence/manifests/sha256/d9be584d7a1eecd43482ea1a05a0d9dd8cd681970c4ec5ff225740a28f27a5bf.jsonl.gz` - manifest detail: compressed `8abf72fa...` / 11,288,256 B; uncompressed `d9be584d...` / 466,717,014 B; 733,203 row records, 0 collisions, 0 rejections, 733,191 pending keys, total 1,466,395 records; consumable_object_count=12; family_object_counts = {daily/indexPriceKlines 12,266; daily/klines 13,710; daily/markPriceKlines 14,096; daily/metrics 573,786; daily/premiumIndexKlines 11,439; monthly/fundingRate 21,035; monthly/indexPriceKlines 21,721; monthly/klines 21,932; monthly/markPriceKlines 22,286; monthly/premiumIndexKlines 20,932}.

## 8. Compact receipt / detail validation (review 133 Required after proof)

All checks performed by invoking the accepted reader/validator against the descriptor published inside the compact report 62.

### Report-62 receipt (compact, valid terminal replacement)

- Valid JSON (json.loads succeeded). OK
- Size: report/sprint_004/62_CEX002_GATE1_SOURCE_PROCUREMENT.json = 17,349,108 B - below the 90,000,000-byte ceiling. OK
- Neither receipt surface (document[acquisition_manifest] = manifest_block; document[storage][acquisition_manifest] = storage_block) carries any of rows, collisions, rejections, raw_validation_pending_keys (forbidden-key scan returned []). OK
- Manifest-block detail == descriptor; storage-block detail == summary (manifest_detail_summary); {name: descriptor[name] for name in summary} == summary; "detail" not in document at top level. OK
- Descriptor relative_path = evidence/manifests/sha256/d9be584d...jsonl.gz - exact uncompressed SHA-256 content address under evidence/manifests/sha256/. OK
- Compressed and uncompressed hashes/sizes reconcile: compressed `8abf72fa...` / 11,288,256 B; uncompressed `d9be584d...` / 466,717,014 B. OK
- Schema/format/header: schema_version=cex002_manifest_detail_v1, format=canonical_jsonl_gzip, reader=iter_manifest_detail, integrity_rule present. OK

### validate_manifest_detail(store_root, descriptor) - accepted reader, single bounded pass

Exit 0 (MANIFEST_DETAIL_VALIDATED=True). Re-proven aggregates (recomputed from the row records, nothing trusted from the header):

| Reconciled field | Value |
|---|---|
| uncompressed_bytes | 466,717,014 (matches descriptor) |
| uncompressed_sha256 | `d9be584d7a1eecd43482ea1a05a0d9dd8cd681970c4ec5ff225740a28f27a5bf` (matches descriptor + filename) |
| compressed_sha256 | `8abf72fa22c6714051c2b451bfd27e17b6c84a65b7e476be63bc21f09f265945` (matches descriptor) |
| compressed_bytes | 11,288,256 (matches descriptor) |
| object_count | 733,203 (matches descriptor) |
| record_counts | row=733,203, collision=0, rejection=0, raw_validation_pending_key=733,191, total_records=1,466,395 (matches descriptor) |
| consumable_object_count | 12 |
| family_object_counts | (see section 7 new-artifact table) |

Enforced in the pass: canonical encoding, record-phase order (header -> collision -> rejection -> raw_validation_pending_key -> row), strict canonical ordering, unique row identities (adjacent duplicates / descending order rejected, only last_key retained), and pending-key reconciliation (raw_validation_pending_key=733,191 reconciled against 733,203 rows). The companion consumer iter_manifest_detail yielded 1,466,394 records from the gzipped stream (header + 1,466,393 data records; total_records=1,466,395 incl. header), in canonical order.

### Required counts (review 133 line 145-equivalent / review 130)

- Detail contains exactly 733,203 row records: OK (object_count=733,203; record_counts.row=733,203; validated through iter_manifest_detail).
- No collection sampled, truncated, or staged: OK (reused_existing=false; record counts reconciled from the stream, not trusted from a header; zero collisions/rejections; the single bounded pass recomputed every aggregate).

## 9. Terminal evidence (gate) state

| Field | Value |
|---|---|
| gate_status | BLOCKED |
| accepted | False |
| symbols | 1004 |
| blocked_products | 7 (binance_usdm_perpetual_membership, binance_usdm_bar_1h, binance_usdm_open_interest_5m, binance_usdm_funding_realized, binance_usdm_funding_indicative_1h, binance_usdm_mark_index_basis_1h, binance_usdm_cost_calibration) |
| membership | basis=confirmed_perpetual_membership, confirmed=771, unresolved=63; classes: confirmed_perpetual 771, dated_delivery_candidate 46, delivery_non_perpetual 4, settlement_artifact_candidate 17, tradifi_perpetual 170 |
| plan_lock | version=2, state=locked, plan_digest=`d6eb52ff...` |
| candidate_plan | state=candidate_unmigrated, version=3, prior_version=2, plan_digest=`0a1c358c...`, envelope_digest=`a14018c2...` |
| migration_authorized | False |
| download_authorized | False |
| samples | [] (empty) |
| holdout | id=`c842f813...`, boundary_utc=2026-08-21T16:19:08.994Z, stream_collector=False |
| listing reuse | reused=39,812, fetched=0, unclaimed=0, serializations=1, workers=8, clients=1/1, retries=0 |

## 10. Mutations

The only artifacts the verified candidate wrote: (a) overwrote in-place research/sprint_004/62_CEX002_GATE1_SOURCE_PROCUREMENT.json (monolith `46d1980e`, 1.06 GB -> compact `e51ef273`, 17,349,108 B); (b) created data/cex002_qualify/evidence/manifests/sha256/d9be584d….jsonl.gz (manifest detail, git-ignored data store); (c) advanced data/cex002_qualify/cex002_qualification_progress.json (`332f2d87...` -> `5c85bbf0...`) and the listing/fixed checkpoint caches (fapi_cache +1 file) as the reuse path. The source monolith was additionally preserved (pre-candidate) to evidence/prior_reports/sha256/46d1980e….json. No plan migration, sample download, amendment-ledger creation, Gate 2, normalization, catalog publication, Nautilus, Harmonic Trader, payoff analysis, PAPER, LIVE, Git LFS, scope reduction, or other-ticket work.

## 11. Stop point / disposition

Stop point: review-130/133 corrected candidate resume completed with candidate_status=2 (terminal evidence, BLOCKED). One invocation only; no second run.

CEX-002 remains IN_PROGRESS. Gate 1 has not passed (gate_status=BLOCKED). Plan migration, sample acquisition, Gate 2, normalization, catalog publication, Nautilus work, Harmonic Trader work, payoff analysis, PAPER, LIVE, and every other ticket remain unauthorized. Next ticket remains NONE.

## 12. Explicit no-op statement

No monolith truncation, no Git LFS, no external artifact service, no report truncation/scope reduction. The 1.06 GB source monolith was preserved byte-for-byte (not edited); the candidate produced the compact replacement. All unrelated dirty DEX/BitMEX/catalog/ingest/config/research paths remain exactly as found, uncommitted.
