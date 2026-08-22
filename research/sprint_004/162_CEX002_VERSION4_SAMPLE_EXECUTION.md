# CEX-002 Version-4 Sample Execution

Date: 2026-08-21
Author: Jr Dev - Hermes
Governing review: `research/sprint_004/161_CEX002_MIGRATION_ACCEPTANCE_AND_SAMPLE_EXECUTION.md`

## 1. Preconditions

Review 161 authorized exactly one direct network-enabled ordinary qualification invocation
for the locked version-4 Gate-1 samples. Hermes did not rerun C1-C5, did not run migration
mode, did not run candidate-plan mode, and did not consume a preliminary restricted-
sandbox attempt.

Before execution:

`HEAD == origin/main == ea82a499c283d64170632053fedf5a40d4ca0fe9`

Accepted source hashes re-proved:

| Path | SHA-256 |
|---|---|
| `src/cryptofactors/acquisition/binance_usdm_harmonic_qualification.py` | `ee9a794d96671763a6321373d70e3ed67d5c2f0c234ba94a234fd14308a9aae5` |
| `scripts/research/qualify_binance_usdm_harmonic_sources.py` | `3b9181366ee4a575d450d06cf70340e1a2cf2c65d5239081f4782ebc9c6e4ced` |
| `tests/acquisition/test_binance_usdm_harmonic_qualification.py` | `5d4b2e2c199b6826e9da6d6561381207644d33c119572995c7211d5cead1c6d4` |

No `python3` qualification process was running.

Accepted migrated state re-proved:

| Evidence | Before result |
|---|---|
| report 62 | 13,946,727 bytes / `f26abbc577307e5dcef693ec159fa65d1373d7b03c2be0eb6b926e5b09f97406` |
| manifest detail | 11,288,256 bytes / `8abf72fa22c6714051c2b451bfd27e17b6c84a65b7e476be63bc21f09f265945` |
| version-4 lock | 425,308 bytes / `8fda3c7db11173dafa122114667622f501b62ecf05f12cdf796897d5af0942bc` |
| preserved version-2 lock | 381,855 bytes / `e04a5ce2f2513cc8a0f4e6698dcbf9d43c5a7bec0295021ca5d431ff886f0d84` |
| amendment ledger | 2,565 bytes / `96c7f9700cf89d73006f6b4234d05e1d2e25a1c766804bdb5cbd479c09d3e1c7` |
| legacy ledger | 777 bytes / `47341a9ca2c60caf73485fb9bac40c6526cb35a13471e4545cd9cdcee6e227f6` |
| sample checkpoint/progress | 299,571 bytes / `b60fe7b6d805f9cc14a67f1256978a742556b94949c3a74b89e1cf597d02ca7f` |
| retry journal | 13,737 bytes / `a9c77e465972a5ab59960519f5e4fab12a63c4767747eaee22e4d12d429b0a24` |
| sample plan | 101,930 bytes / `02752b25d9fcfb1b9e4602bde23c8847f870578218e882213b56290b94704c12` |
| listing checkpoint | 33,206,753 bytes / `d584e22aaaa9414b06dbe13bc24dda0b01ed48e37bdf66f5b42f90865959bf9a` |
| official contract metadata | 98,523 bytes / `8def15228d2272bc85d2466d243c55d25b953ccaa414f91bd637a1e9bf9169bb` |
| retained raw tree | 186 files / 1,015,198,547 bytes |
| list cache | 40,961 files |
| FAPI cache | 15 files |
| Coinalyze cache | 7 files |
| available bytes | 170,219,610,112 |

The read-only migrated-state preflight returned `version_4_lock_installed`, prepared
ledger path `data/cex002_qualify/cex002_amendment_ledger.json`, plan digest
`2fb0e47a3666f0e87b35dd7fdd6ea26aa352e34acf8dfd5debf590409aecbbef`, and
`download_authorized=False`.

The lock/ledger binding matched exactly. The lock had `plan_version=4`, history versions
`[0, 1, 2]`, superseded candidate version `[3]`, and `download_authorized=False`. The
amendment ledger had budget bytes `268435456`, empty charges, empty reservations, binding
state `prepared_for_reviewed_v4_migration`, production source hash
`ee9a794d96671763a6321373d70e3ed67d5c2f0c234ba94a234fd14308a9aae5`, and executing
code/config digest `8613b4f6f42ad32c09099362fb0ea817a2f2a660bfd3b5dc322ebea0fd207e4e`.

## 2. Accepted-report preservation

Before ordinary execution could overwrite report 62, Hermes preserved its exact accepted
bytes at:

`data/cex002_qualify/evidence/prior_reports/sha256/f26abbc577307e5dcef693ec159fa65d1373d7b03c2be0eb6b926e5b09f97406.json`

The destination did not exist. Hermes created the parent directory, copied report 62 to a
temporary file using `cp --reflink=never`, rehashed the temporary copy to
`f26abbc577307e5dcef693ec159fa65d1373d7b03c2be0eb6b926e5b09f97406`, atomically renamed it
without replacing a different destination, and re-proved the final file at 13,946,727
bytes and the same SHA-256. This ignored data evidence was not staged.

## 3. One ordinary qualification invocation

Hermes requested and received approval to run the command outside the restricted sandbox
with network access before launch.

`.env` was loaded only into the process environment. Hermes made exactly one foreground
ordinary invocation:

```bash
set -a
. ./.env
set +a
timeout --signal=TERM --kill-after=60s 50m \
  .venv/bin/python scripts/research/qualify_binance_usdm_harmonic_sources.py \
    --store-root data/cex002_qualify \
    --progress-path data/cex002_qualify/cex002_qualification_progress.json \
    --report-path research/sprint_004/62_CEX002_GATE1_SOURCE_PROCUREMENT.json
```

Start: `2026-08-21T20:25:31-07:00`

End: `2026-08-21T20:39:20-07:00`

Elapsed seconds: 829

Exit/status: `2`

Status 2 is a valid terminal report with Gate 1 still blocked.

Transcript:

```text
qualification_start=2026-08-21T20:25:31-07:00
listing checkpoint bootstrap: claimed=0 checksum_blobs=186 skipped_already_bound=40771 unclaimed=0
Qualification report written to research/sprint_004/62_CEX002_GATE1_SOURCE_PROCUREMENT.json
manifest_detail: path=evidence/manifests/sha256/d6c1fac650aaf16d88750da2a40d837f543d0c5fc88c73d463753a576d5bdd17.jsonl.gz uncompressed_sha256=d6c1fac650aaf16d88750da2a40d837f543d0c5fc88c73d463753a576d5bdd17 uncompressed_bytes=466714158 compressed_sha256=64d0f74b8e4696c98d0f96423185fd961aba6c63348d12425e3ec364b888f113 compressed_bytes=11292635 records={'row': 733203, 'collision': 0, 'rejection': 0, 'raw_validation_pending_key': 733147, 'total_records': 1466351} reused_existing=False
gate_status=BLOCKED accepted=False symbols=1004 blocked=['binance_usdm_perpetual_membership', 'binance_usdm_bar_1h', 'binance_usdm_open_interest_5m', 'binance_usdm_funding_realized', 'binance_usdm_funding_indicative_1h', 'binance_usdm_mark_index_basis_1h', 'binance_usdm_cost_calibration']
sample_plan: planned_new_bytes=1049324 budget=268435456 retained_bytes=44642 budget_blocked=0
plan_lock: version=4 state=locked plan_digest=2fb0e47a3666f0e87b35dd7fdd6ea26aa352e34acf8dfd5debf590409aecbbef superseded=[0, 1, 2]
budget: charged=1049324 spent_range=[1049324,1049324] remaining=267386132 reserved=203853 legacy_state=resolved breach_state=none
membership: basis=confirmed_perpetual_membership confirmed=771 unresolved=0 classes={'confirmed_perpetual': 771, 'delivery_non_perpetual': 4, 'official_archive_settlement_alias': 17, 'reviewed_delivery_non_perpetual': 46, 'tradifi_perpetual': 170}
gate2_storage: state=unknown selected_raw_bytes=7833966625 cost_sample_bytes=12522974218 projected_new_bytes=20351919280 available_bytes=169556369408 total_required_bytes=None unknown_components=['normalized_catalog_bytes', 'temporary_high_water_bytes', 'operating_reserve_bytes']
candidate_plan: state=not_constructed version=4 prior_version=None plan_digest=None envelope_digest=None migration_authorized=False download_authorized=False
holdout: id=c842f813839e1dda375b351da0f693c54bcf932e33eb6e3394aba860c12346e2 boundary_utc=2026-08-21T16:19:08.994166+00:00 stream_collector=False
listing_checkpoint: reused=39812 fetched=0 unclaimed=0 serializations=1 | workers=8 clients=1/1 retries=0
ERROR: incomplete product matrix is refused | context={'gate_status': 'BLOCKED', 'blocked_products': ['binance_usdm_perpetual_membership', 'binance_usdm_bar_1h', 'binance_usdm_open_interest_5m', 'binance_usdm_funding_realized', 'binance_usdm_funding_indicative_1h', 'binance_usdm_mark_index_basis_1h', 'binance_usdm_cost_calibration']}
qualification_end=2026-08-21T20:39:20-07:00
qualification_elapsed_seconds=829
qualification_status=2
```

## 4. Report and manifest detail

The changed report is valid JSON:

| Evidence | After result |
|---|---|
| report 62 | 13,944,475 bytes / `53f8f93379cb55d66b6de062f1a6a85f4c9dd318f5b41cc047bff2f5feeaaf51` |
| gate status | `BLOCKED` |
| accepted | `false` |
| generated at | `2026-08-22T03:25:33.763453+00:00` |
| manifest detail compressed path | `data/cex002_qualify/evidence/manifests/sha256/d6c1fac650aaf16d88750da2a40d837f543d0c5fc88c73d463753a576d5bdd17.jsonl.gz` |
| manifest detail compressed SHA-256 | `64d0f74b8e4696c98d0f96423185fd961aba6c63348d12425e3ec364b888f113` |
| manifest detail compressed bytes | 11,292,635 |
| manifest detail uncompressed SHA-256 | `d6c1fac650aaf16d88750da2a40d837f543d0c5fc88c73d463753a576d5bdd17` |
| manifest detail uncompressed bytes | 466,714,158 |
| manifest detail records | rows 733,203; collisions 0; rejections 0; raw-validation-pending keys 733,147; total records 1,466,351 |

Blocked products remain:

- `binance_usdm_perpetual_membership`
- `binance_usdm_bar_1h`
- `binance_usdm_open_interest_5m`
- `binance_usdm_funding_realized`
- `binance_usdm_funding_indicative_1h`
- `binance_usdm_mark_index_basis_1h`
- `binance_usdm_cost_calibration`

## 5. Sample accounting and plan boundaries

The locked plan contained exactly 106 entries:

- 84 `download` entries totaling 1,049,324 planned bytes;
- 12 `reuse_retained` entries totaling 44,642 bytes;
- 10 `alias` entries totaling 22,307 alias-referenced bytes; and
- zero budget-blocked entries.

The post-run report contained 104 sample records:

- 90 records with `reused_existing=false`;
- 14 records with `reused_existing=true`;
- product counts: 20 `binance_usdm_bar_1h`, 4 `binance_usdm_cost_calibration`,
  20 `binance_usdm_funding_indicative_1h`, 10 `binance_usdm_funding_realized`,
  40 `binance_usdm_mark_index_basis_1h`, and 10 `binance_usdm_open_interest_5m`;
- sample byte sum: 912,420.

Raw tree growth independently proves the 84 locked new object identities were acquired:
the raw tree advanced from 186 files / 1,015,198,547 bytes to 270 files /
1,016,247,871 bytes, exactly +84 files and +1,049,324 bytes. No out-of-plan raw-file count
or byte growth was observed.

The report's retry section records 177 attempts and 0 retries. No retry incidents were
reported.

## 6. Ledger, checkpoint, and cache after-proof

After snapshot:

| Evidence | After result |
|---|---|
| version-4 lock | 425,308 bytes / `8fda3c7db11173dafa122114667622f501b62ecf05f12cdf796897d5af0942bc` |
| preserved version-2 lock | 381,855 bytes / `e04a5ce2f2513cc8a0f4e6698dcbf9d43c5a7bec0295021ca5d431ff886f0d84` |
| amendment ledger | 25,223 bytes / `2a4c4db6e14350d6814b6f72a3caa1357659cd064a13fd2edeb84a2896223c8c` |
| legacy ledger | 777 bytes / `47341a9ca2c60caf73485fb9bac40c6526cb35a13471e4545cd9cdcee6e227f6` |
| sample checkpoint/progress | 395,626 bytes / `d6c327faa144e819ca6fd4c7b0325b4a39b3ecb7cf1daa2bfdb747b2f22e85ee` |
| retry journal | 13,737 bytes / `a9c77e465972a5ab59960519f5e4fab12a63c4767747eaee22e4d12d429b0a24` |
| sample plan | 51,124 bytes / `02f8e435b18643586ff6e778bfd85cffd0136457b5dcf8466f5a24c35e2f2d18` |
| listing checkpoint | 33,206,753 bytes / `d584e22aaaa9414b06dbe13bc24dda0b01ed48e37bdf66f5b42f90865959bf9a` |
| official contract metadata | 98,940 bytes / `19bfa0e3314a5e2204bca68fae8dcb4583d58f886792fe615aeb4f973916f2b8` |
| raw tree | 270 files / 1,016,247,871 bytes / listing digest `0fe95c8a74d15a26f4d7b12caeae75377ec4a57ee9a32d9149258f607651da23` |
| list cache | 41,045 files / 5,158,280,401 bytes / listing digest `12e89ce570611dfe4bc95e447981ff71c6c5b031f1703ebc9c2b964234369817` |
| FAPI cache | 16 files / 14,009,673 bytes / listing digest `f2532c165ada6403b98cbc3b8f006e770970743b8a631a984a7dbe0e0514dc85` |
| Coinalyze cache | 7 files / 3,144,369 bytes / listing digest `b444c023db10fd8fa3788c46c4363034e8a918081504758761f8c45f7ef4a338` |
| available bytes | 169,504,616,448 |

The version-4 lock remained byte-identical. The content-addressed prior report and prior
version-2 lock remained byte-identical. The legacy ledger remained byte-identical and
lineage-only. The listing checkpoint remained byte-identical. The retry journal remained
byte-identical after the ordinary run.

The amendment ledger recorded:

- budget bytes `268435456`;
- charged bytes `1049324`;
- remaining bytes `267386132`;
- 82 charged transfer entries with transferred/planned bytes totaling 845,471;
- 2 outstanding reservations totaling 203,853 planned bytes:
  - `data/futures/um/daily/bookTicker/LTCBUSD/LTCBUSD-bookTicker-2023-08-25.zip` at 317 planned bytes;
  - `data/futures/um/daily/bookTicker/XRPUSDC/XRPUSDC-bookTicker-2024-01-04.zip` at 203,536 planned bytes.

The reserved bytes plus charged transfer bytes equal the 1,049,324 planned new bytes and
remain below the 268,435,456-byte allowance. Hermes does not resolve, retry, restore, or
mutate those reservations because review 161 authorizes no second invocation.

## 7. Terminal disposition

Gate 1 remains blocked. No migration, candidate-plan generation, automatic resume, second
qualification invocation, further retry, Gate 2, normalization, catalog publication,
Nautilus work, Harmonic Trader work, payoff analysis, PAPER, LIVE, paid source, reduced
scope, or next-ticket work occurred.

For status 2 with a valid changed report, review 161 authorizes staging exactly the two
controls, report 62, and this record.
