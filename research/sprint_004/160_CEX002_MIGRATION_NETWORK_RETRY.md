# CEX-002 Migration Network Retry

Date: 2026-08-21
Author: Jr Dev - Hermes
Governing review: `research/sprint_004/159_CEX002_MIGRATION_NETWORK_FAILURE_REVIEW.md`

## 1. Authorization and preconditions

Review 159 authorized exactly one direct network-enabled
`--apply-reviewed-v4-migration-only` retry. Hermes did not rerun C1-C5 and did not consume
a preliminary sandboxed migration attempt.

Before the retry, Hermes established:

`HEAD == origin/main == 3dc9ce4a77133cc76c4f6b73839b427de19454cc`

Accepted source hashes re-proved:

| Path | SHA-256 |
|---|---|
| `src/cryptofactors/acquisition/binance_usdm_harmonic_qualification.py` | `ee9a794d96671763a6321373d70e3ed67d5c2f0c234ba94a234fd14308a9aae5` |
| `scripts/research/qualify_binance_usdm_harmonic_sources.py` | `3b9181366ee4a575d450d06cf70340e1a2cf2c65d5239081f4782ebc9c6e4ced` |
| `tests/acquisition/test_binance_usdm_harmonic_qualification.py` | `5d4b2e2c199b6826e9da6d6561381207644d33c119572995c7211d5cead1c6d4` |

No `python3` qualification process was running.

Accepted retry precondition table re-proved:

| Evidence | Result |
|---|---|
| report 62 | 13,946,727 bytes / `f26abbc577307e5dcef693ec159fa65d1373d7b03c2be0eb6b926e5b09f97406` |
| manifest detail | 11,288,256 bytes / `8abf72fa22c6714051c2b451bfd27e17b6c84a65b7e476be63bc21f09f265945` |
| version-2 lock | 381,855 bytes / `e04a5ce2f2513cc8a0f4e6698dcbf9d43c5a7bec0295021ca5d431ff886f0d84` |
| legacy ledger | 777 bytes / `47341a9ca2c60caf73485fb9bac40c6526cb35a13471e4545cd9cdcee6e227f6` |
| sample checkpoint/progress | 299,571 bytes / `b60fe7b6d805f9cc14a67f1256978a742556b94949c3a74b89e1cf597d02ca7f` |
| retry journal | 13,737 bytes / `a9c77e465972a5ab59960519f5e4fab12a63c4767747eaee22e4d12d429b0a24` |
| amendment ledger | absent |
| retained raw tree | 186 files / 1,015,198,547 bytes |
| available bytes | 170,521,219,072 |

The read-only migration preflight returned state `not_started`, no prepared ledger,
accepted report SHA-256 `f26abbc577307e5dcef693ec159fa65d1373d7b03c2be0eb6b926e5b09f97406`,
prior-lock SHA-256 `e04a5ce2f2513cc8a0f4e6698dcbf9d43c5a7bec0295021ca5d431ff886f0d84`,
legacy-ledger SHA-256 `47341a9ca2c60caf73485fb9bac40c6526cb35a13471e4545cd9cdcee6e227f6`,
candidate plan digest `2fb0e47a3666f0e87b35dd7fdd6ea26aa352e34acf8dfd5debf590409aecbbef`,
and `download_authorized=False`.

## 2. Network authorization and single invocation

Hermes requested and received approval to run the command outside the restricted sandbox
with network access before launching the migration retry.

`.env` was loaded only into the process environment. Hermes made exactly one foreground
invocation:

```bash
set -a
. ./.env
set +a
timeout --signal=TERM --kill-after=60s 50m \
  .venv/bin/python scripts/research/qualify_binance_usdm_harmonic_sources.py \
    --store-root data/cex002_qualify \
    --progress-path data/cex002_qualify/cex002_qualification_progress.json \
    --report-path research/sprint_004/62_CEX002_GATE1_SOURCE_PROCUREMENT.json \
    --apply-reviewed-v4-migration-only
```

Start: `2026-08-21T20:05:45-07:00`

End: `2026-08-21T20:15:00-07:00`

Elapsed seconds: 555

Exit/status: `2`

Status 2 is the expected terminal status after a successful migration because Gate 1
remains blocked.

Transcript:

```text
migration_start=2026-08-21T20:05:45-07:00
listing checkpoint bootstrap: claimed=0 checksum_blobs=186 skipped_already_bound=40771 unclaimed=0
reviewed_v4_migration: {"accepted_code_config_digest": "3764a547c579394ef8743d7bf0b7919a4c5aff1ef980e2be012a779bd4c44978", "allowance_bytes": 268435456, "allowance_charged_bytes": 0, "amendment_ledger_id": "cex002_architecture_amendment_v3", "amendment_ledger_path": "data/cex002_qualify/cex002_amendment_ledger.json", "candidate_envelope_digest": "be63989bd4d3d40c95c7ca405eae7558ce0ef997a2289892d14ed8d773d4cbfe", "complete_cost_manifest_digest": "04842ff6b9b58280b3ec2ea2644b3d44769be62d460bef785262cd4dd65cac57", "download_authorized": false, "executed": true, "executing_code_config_digest": "8613b4f6f42ad32c09099362fb0ea817a2f2a660bfd3b5dc322ebea0fd207e4e", "legacy_ledger_role": "preserved_lineage_only", "legacy_ledger_sha256": "47341a9ca2c60caf73485fb9bac40c6526cb35a13471e4545cd9cdcee6e227f6", "migrated_at": "2026-08-22T03:05:47.039320+00:00", "migration_authorized": true, "migration_id": "cex002_reviewed_v4_migration", "note": "ledger-first, lock-last, one shot. This transition installs the reviewed version-4 plan and authorizes no sample download", "plan_digest": "2fb0e47a3666f0e87b35dd7fdd6ea26aa352e34acf8dfd5debf590409aecbbef", "plan_shape": {"aliases": 10, "blocked": 0, "entries": 106, "new_bytes": 1049324, "new_objects": 84, "retained_bytes": 44642, "retained_objects": 12}, "plan_version": 4, "preserved_plan_versions": [0, 1, 2], "prior_lock_evidence_path": "data/cex002_qualify/evidence/locks/sha256/e04a5ce2f2513cc8a0f4e6698dcbf9d43c5a7bec0295021ca5d431ff886f0d84.json", "prior_lock_sha256": "e04a5ce2f2513cc8a0f4e6698dcbf9d43c5a7bec0295021ca5d431ff886f0d84", "prior_plan_version": 2, "report_path": "research/sprint_004/62_CEX002_GATE1_SOURCE_PROCUREMENT.json", "report_sha256": "f26abbc577307e5dcef693ec159fa65d1373d7b03c2be0eb6b926e5b09f97406", "samples_acquired": 0, "source_config_advanced": true, "source_identity": {"alias_table_sha256": "e9837ee2ac0711e41981e27979532be5095d61f04fb82442919c9f301f5998f8", "code_config_digest": "8613b4f6f42ad32c09099362fb0ea817a2f2a660bfd3b5dc322ebea0fd207e4e", "delivery_table_sha256": "678d07e0679b0e116a372a333c3c33f74f5e421dadba393cb9516e56ae8b9a01", "module_sha256": "ee9a794d96671763a6321373d70e3ed67d5c2f0c234ba94a234fd14308a9aae5", "reviewed_authority_table_version": "review137-v1"}, "state": "version_4_lock_installed"}
gate_status=BLOCKED accepted=False symbols=1004 blocked=['binance_usdm_perpetual_membership', 'binance_usdm_bar_1h', 'binance_usdm_open_interest_5m', 'binance_usdm_funding_realized', 'binance_usdm_funding_indicative_1h', 'binance_usdm_mark_index_basis_1h', 'binance_usdm_cost_calibration']
sample_plan: planned_new_bytes=1049324 budget=268435456 retained_bytes=44642 budget_blocked=0
plan_lock: version=4 state=locked plan_digest=2fb0e47a3666f0e87b35dd7fdd6ea26aa352e34acf8dfd5debf590409aecbbef superseded=[0, 1, 2]
budget: charged=0 spent_range=[0,0] remaining=268435456 reserved=0 legacy_state=resolved breach_state=none
membership: basis=confirmed_perpetual_membership confirmed=771 unresolved=0 classes={'confirmed_perpetual': 771, 'delivery_non_perpetual': 4, 'official_archive_settlement_alias': 17, 'reviewed_delivery_non_perpetual': 46, 'tradifi_perpetual': 170}
gate2_storage: state=unknown selected_raw_bytes=7833966625 cost_sample_bytes=12522974218 projected_new_bytes=20352428237 available_bytes=170196897792 total_required_bytes=None unknown_components=['normalized_catalog_bytes', 'temporary_high_water_bytes', 'operating_reserve_bytes']
candidate_plan: state=migrated_reviewed_v4 version=4 prior_version=None plan_digest=None envelope_digest=None migration_authorized=True download_authorized=False
holdout: id=c842f813839e1dda375b351da0f693c54bcf932e33eb6e3394aba860c12346e2 boundary_utc=2026-08-21T16:19:08.994166+00:00 stream_collector=False
listing_checkpoint: reused=39812 fetched=0 unclaimed=0 serializations=1 | workers=8 clients=1/1 retries=0
ERROR: incomplete product matrix is refused | context={'gate_status': 'BLOCKED', 'blocked_products': ['binance_usdm_perpetual_membership', 'binance_usdm_bar_1h', 'binance_usdm_open_interest_5m', 'binance_usdm_funding_realized', 'binance_usdm_funding_indicative_1h', 'binance_usdm_mark_index_basis_1h', 'binance_usdm_cost_calibration']}
migration_end=2026-08-21T20:15:00-07:00
migration_elapsed_seconds=555
migration_status=2
```

## 3. After-proof

After snapshot:

| Evidence | Result |
|---|---|
| report 62 | 13,946,727 bytes / `f26abbc577307e5dcef693ec159fa65d1373d7b03c2be0eb6b926e5b09f97406` |
| manifest detail | 11,288,256 bytes / `8abf72fa22c6714051c2b451bfd27e17b6c84a65b7e476be63bc21f09f265945` |
| sample plan lock | 425,308 bytes / `8fda3c7db11173dafa122114667622f501b62ecf05f12cdf796897d5af0942bc` |
| preserved prior-lock evidence | 381,855 bytes / `e04a5ce2f2513cc8a0f4e6698dcbf9d43c5a7bec0295021ca5d431ff886f0d84` |
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
| available bytes | 170,189,721,600 |

The post-migration read-only preflight returned state `version_4_lock_installed`,
accepted report SHA-256 `f26abbc577307e5dcef693ec159fa65d1373d7b03c2be0eb6b926e5b09f97406`,
legacy-ledger SHA-256 `47341a9ca2c60caf73485fb9bac40c6526cb35a13471e4545cd9cdcee6e227f6`,
prepared ledger path `data/cex002_qualify/cex002_amendment_ledger.json`, candidate plan
digest `2fb0e47a3666f0e87b35dd7fdd6ea26aa352e34acf8dfd5debf590409aecbbef`, and
`download_authorized=False`.

The installed lock has `plan_version=4`, plan digest
`2fb0e47a3666f0e87b35dd7fdd6ea26aa352e34acf8dfd5debf590409aecbbef`, preserved history
versions `[0, 1, 2]`, preserved superseded candidate version `[3]`, and
`download_authorized=False`.

The amendment ledger has kind `budget_ledger`, version `1`, budget bytes `268435456`,
empty `charges`, empty `reservations`, binding state `prepared_for_reviewed_v4_migration`,
binding plan digest `2fb0e47a3666f0e87b35dd7fdd6ea26aa352e34acf8dfd5debf590409aecbbef`,
binding source module SHA-256 `ee9a794d96671763a6321373d70e3ed67d5c2f0c234ba94a234fd14308a9aae5`,
binding source code/config digest `8613b4f6f42ad32c09099362fb0ea817a2f2a660bfd3b5dc322ebea0fd207e4e`,
and `download_authorized=False`. The ledger binding exactly matches the installed lock's
amendment binding.

## 4. Mutations and terminal state

The migration intentionally installed the reviewed version-4 lock, preserved the prior
version-2 lock content-addressably, and created the amendment ledger.

Observed state/cache mutations:

- `data/cex002_qualify/cex002_sample_plan_lock.json` advanced from the accepted version-2
  lock to the version-4 lock.
- `data/cex002_qualify/evidence/locks/sha256/e04a5ce2f2513cc8a0f4e6698dcbf9d43c5a7bec0295021ca5d431ff886f0d84.json`
  was created with the exact prior-lock bytes.
- `data/cex002_qualify/cex002_amendment_ledger.json` was created.
- FAPI cache advanced from 14 to 15 files; the new observed cache entry was
  `data/cex002_qualify/fapi_cache/bbab355b309ae08994afc8b7cd65115721f7406baa5873f4ffe8cec3ad33c3aa`,
  1,077,582 bytes.

The accepted report, manifest detail, legacy ledger, sample checkpoint/progress, retry
journal, sample plan, listing checkpoint, official contract metadata, retained raw tree,
list cache count, and Coinalyze cache count remained unchanged. No samples were acquired.
No ordinary resume, further retry, second migration command, Gate 2, normalization, catalog
publication, Nautilus work, Harmonic Trader work, payoff analysis, PAPER, LIVE, or
next-ticket work occurred.

Gate 1 remains blocked. The terminal product matrix still reports blocked products:
`binance_usdm_perpetual_membership`, `binance_usdm_bar_1h`,
`binance_usdm_open_interest_5m`, `binance_usdm_funding_realized`,
`binance_usdm_funding_indicative_1h`, `binance_usdm_mark_index_basis_1h`, and
`binance_usdm_cost_calibration`.

## 5. Publication

This record publishes the single network-enabled migration-only retry and its terminal
state. CEX-002 remains `IN_PROGRESS`; Gate 1 has not passed; next ticket remains `NONE`.
