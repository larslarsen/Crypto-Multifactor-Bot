# CEX-002 Corrected Qualification Execution

Date: 2026-08-21
Actor: Jr Dev - Hermes
Ticket: CEX-002

## Scope

Review 177 authorized exactly one network-enabled corrected ordinary qualification run,
after preproof and preservation of the accepted report 62 bytes.

No second invocation, retry, resume, source correction, migration, candidate construction,
full-history or bulk acquisition, Gate 1 acceptance, Gate 2, normalization, catalog
publication, Nautilus work, Harmonic Trader work, payoff analysis, PAPER, LIVE, paid
source, reduced scope, or next-ticket work was run.

## Preproof

`git rev-parse HEAD origin/main`

```text
d344ca4cd23f35b8b85c5efad8a6cebeb82285b5
d344ca4cd23f35b8b85c5efad8a6cebeb82285b5
```

Accepted source hashes:

```text
068763e2359abf4fc4fe4b7e7fdea95495db5c22bf362d468fec4056775ecb7e  src/cryptofactors/acquisition/binance_usdm_harmonic_qualification.py
473185ca946dcc37d506d8891e8f955708ff80c976a586967762c1294956d28f  scripts/research/qualify_binance_usdm_harmonic_sources.py
4cf2b786e95723f933a293b8bfdfb59236cfad8490ec7afcbadecc347e543ff0  tests/acquisition/test_binance_usdm_harmonic_qualification.py
```

`rg -c '^def test_' tests/acquisition/test_binance_usdm_harmonic_qualification.py`

```text
305
```

`ps -C python3 -o pid=,args=` exited 1 with no output.

The prior-report destination was absent before preservation:

```text
data/cex002_qualify/evidence/prior_reports/sha256/53f8f93379cb55d66b6de062f1a6a85f4c9dd318f5b41cc047bff2f5feeaaf51.json
```

Accepted artifact sizes and hashes before execution:

```text
13944475 / 53f8f93379cb55d66b6de062f1a6a85f4c9dd318f5b41cc047bff2f5feeaaf51  research/sprint_004/62_CEX002_GATE1_SOURCE_PROCUREMENT.json
11292635 / 64d0f74b8e4696c98d0f96423185fd961aba6c63348d12425e3ec364b888f113  data/cex002_qualify/evidence/manifests/sha256/d6c1fac650aaf16d88750da2a40d837f543d0c5fc88c73d463753a576d5bdd17.jsonl.gz
426276 / 522271238e38a3652f9521b236981544782e02459450703f21e9ef344d476fa6  data/cex002_qualify/cex002_sample_plan_lock.json
25797 / 832228fd2b4b9394e205a69441281ddbfccc92c227144c5c0c2b8181e164e488  data/cex002_qualify/cex002_amendment_ledger.json
425308 / 8fda3c7db11173dafa122114667622f501b62ecf05f12cdf796897d5af0942bc  data/cex002_qualify/evidence/locks/sha256/8fda3c7db11173dafa122114667622f501b62ecf05f12cdf796897d5af0942bc.json
25223 / 2a4c4db6e14350d6814b6f72a3caa1357659cd064a13fd2edeb84a2896223c8c  data/cex002_qualify/evidence/ledgers/sha256/2a4c4db6e14350d6814b6f72a3caa1357659cd064a13fd2edeb84a2896223c8c.json
777 / 47341a9ca2c60caf73485fb9bac40c6526cb35a13471e4545cd9cdcee6e227f6  data/cex002_qualify/cex002_budget_ledger.json
395626 / d6c327faa144e819ca6fd4c7b0325b4a39b3ecb7cf1daa2bfdb747b2f22e85ee  data/cex002_qualify/cex002_qualification_progress.json
13737 / a9c77e465972a5ab59960519f5e4fab12a63c4767747eaee22e4d12d429b0a24  data/cex002_qualify/cex002_retry_journal.json
51124 / 02f8e435b18643586ff6e778bfd85cffd0136457b5dcf8466f5a24c35e2f2d18  data/cex002_qualify/cex002_sample_plan.json
33206753 / d584e22aaaa9414b06dbe13bc24dda0b01ed48e37bdf66f5b42f90865959bf9a  data/cex002_qualify/cex002_listing_checkpoint.json
98940 / 19bfa0e3314a5e2204bca68fae8dcb4583d58f886792fe615aeb4f973916f2b8  data/cex002_qualify/cex002_official_contract_metadata.json
```

Corrected authority binding before execution:

```text
lock: plan_version=4 plan_digest=2fb0e47a3666f0e87b35dd7fdd6ea26aa352e34acf8dfd5debf590409aecbbef
lock: input_code_config=da33197203e0c9651dc84f42e6e2ce26867339cebe4c68286a00639046c08258 receipts=2
ledger: plan_version=4 plan_digest=2fb0e47a3666f0e87b35dd7fdd6ea26aa352e34acf8dfd5debf590409aecbbef receipts=2
ledger: charges=82 transferred=845471 charged=1049324 reservations=2 reservation_bytes=203853 allowance=268435456 download_authorized=false
```

Available bytes before execution:

```text
166,896,631,808
```

Pre-execution deterministic tree identities:

```text
8577f80bc794dab4fe7b98aa8566118aa4ccac7a05c603aed2914b17ec5889f1 files=270 bytes=1016247871 path=data/cex002_qualify/raw
d97420a075224d6639e894a5c98e848dbb4abccc581f0d6cf5fa356054b470bf files=41045 bytes=5158280401 path=data/cex002_qualify/list_cache
03ea6b726d4518f541ada5b9889cff42955a0eb2ab7e804711649da297602da2 files=16 bytes=14009673 path=data/cex002_qualify/fapi_cache
8499543d5220f1cb71b43d78e73c67a87147d775f95090a485506bf6e0d30e87 files=5 bytes=5387946 path=data/cex002_qualify/fapi_snapshots
5bf18914908474688bdfeea6563e334f8742b7406ee5c2b5b781823865440eec files=7 bytes=3144369 path=data/cex002_qualify/coinalyze_cache
ff62cf6b3beb2eb877fbeff96ec99517ab18f753d307ec9b93ccb82dc22ec77b files=3 bytes=1090593382 path=data/cex002_qualify/evidence/prior_reports
a4dfa97d0cd15c67a38a55f1fde62962b67a0762a9c17ad49c4b8e656be34e67 files=2 bytes=22580891 path=data/cex002_qualify/evidence/manifests
2bbeeaeaa1cb5b0d3b6913279e1cc65e1a9711cd0e9464b69309d14846e94af2 files=2 bytes=807163 path=data/cex002_qualify/evidence/locks
e64b9308f13f8165f6c8672059896982372a2c50cfe2ea1f6ffbfe151ff6a11d files=1 bytes=25223 path=data/cex002_qualify/evidence/ledgers
```

## Report preservation

The accepted report 62 bytes were copied through a collision-safe temporary file and then
published to the required content-addressed prior-report path. The temporary copy and
final file both rehashed to the accepted report hash.

```text
13944475 / 53f8f93379cb55d66b6de062f1a6a85f4c9dd318f5b41cc047bff2f5feeaaf51  data/cex002_qualify/evidence/prior_reports/sha256/53f8f93379cb55d66b6de062f1a6a85f4c9dd318f5b41cc047bff2f5feeaaf51.json
```

## Qualification command

The command loaded `.env` only into the child process environment and ran once:

```bash
set -a
. ./.env
set +a
timeout --signal=TERM --kill-after=60s 50m \
  .venv/bin/python scripts/research/qualify_binance_usdm_harmonic_sources.py \
    --store-root data/cex002_qualify \
    --progress-path data/cex002_qualify/cex002_qualification_progress.json \
    --report-path research/sprint_004/62_CEX002_GATE1_SOURCE_PROCUREMENT.json
qualification_status=$?
```

Transcript:

```text
listing checkpoint bootstrap: claimed=0 checksum_blobs=270 skipped_already_bound=40771 unclaimed=0
Qualification report written to research/sprint_004/62_CEX002_GATE1_SOURCE_PROCUREMENT.json
manifest_detail: path=evidence/manifests/sha256/1d21de4d68fb0dfd330dc480a0d27ddf2216c3b7d5e93b13ff70ea26230f968d.jsonl.gz uncompressed_sha256=1d21de4d68fb0dfd330dc480a0d27ddf2216c3b7d5e93b13ff70ea26230f968d uncompressed_bytes=466713055 compressed_sha256=576b3d7b03ff16fd492c5a9382e35f65e54d73ef3996c3a7fe5c6e6ba49b0fb4 compressed_bytes=11294610 records={'row': 733203, 'collision': 0, 'rejection': 0, 'raw_validation_pending_key': 733130, 'total_records': 1466334} reused_existing=False
gate1_source_blockers:
release_blockers: binance_usdm_bar_1h,binance_usdm_trade_flow_1h,binance_usdm_open_interest_5m,binance_usdm_funding_realized,binance_usdm_funding_indicative_1h,binance_usdm_mark_index_basis_1h,binance_usdm_cost_calibration
gate_status=QUALIFIED accepted=True symbols=1004 blocked=[]
sample_plan: planned_new_bytes=1049324 budget=268435456 retained_bytes=44642 budget_blocked=0
plan_lock: version=4 state=locked plan_digest=2fb0e47a3666f0e87b35dd7fdd6ea26aa352e34acf8dfd5debf590409aecbbef superseded=[0, 1, 2]
budget: charged=1049324 spent_range=[1049324,1049324] remaining=267386132 reserved=0 legacy_state=resolved breach_state=none
membership: basis=confirmed_perpetual_membership confirmed=771 unresolved=0 classes={'confirmed_perpetual': 771, 'delivery_non_perpetual': 4, 'official_archive_settlement_alias': 17, 'reviewed_delivery_non_perpetual': 46, 'tradifi_perpetual': 170}
gate2_storage: state=unknown selected_raw_bytes=7833966625 cost_sample_bytes=12522974218 projected_new_bytes=20351715427 available_bytes=166896631808 total_required_bytes=None unknown_components=['normalized_catalog_bytes', 'temporary_high_water_bytes', 'operating_reserve_bytes']
candidate_plan: state=not_constructed version=4 prior_version=None plan_digest=None envelope_digest=None migration_authorized=False download_authorized=False
holdout: id=c842f813839e1dda375b351da0f693c54bcf932e33eb6e3394aba860c12346e2 boundary_utc=2026-08-21T16:19:08.994166+00:00 stream_collector=False
listing_checkpoint: reused=39812 fetched=0 unclaimed=0 serializations=1 | workers=8 clients=1/1 retries=0
start_utc=2026-08-22T06:05:07Z
end_utc=2026-08-22T06:14:59Z
elapsed_seconds=592
qualification_status=0
```

## Report after-proof

The current report is valid JSON and is a compact receipt backed by a content-addressed
manifest-detail artifact. Current report identity:

```text
13559766 / bf01f88976e2ac3d224e843f340de726f5c8c337ba56a50f9e3c6f75c4d6f227  research/sprint_004/62_CEX002_GATE1_SOURCE_PROCUREMENT.json
```

Top-level report result:

```text
gate_status=QUALIFIED
accepted=true
source_blocked_products=[]
release_blocked_products=[
  binance_usdm_bar_1h,
  binance_usdm_trade_flow_1h,
  binance_usdm_open_interest_5m,
  binance_usdm_funding_realized,
  binance_usdm_funding_indicative_1h,
  binance_usdm_mark_index_basis_1h,
  binance_usdm_cost_calibration
]
product_count=11
```

Product matrix summary:

```text
binance_usdm_perpetual_membership: official_qualified, coverage complete, source_blocked=false, release_blocked=false, samples=0
binance_usdm_bar_1h: official_qualified, blocking_gaps, source_blocked=false, release_blocked=true, samples=20
binance_usdm_trade_flow_1h: official_qualified, blocking_gaps, source_blocked=false, release_blocked=true, samples=0
binance_usdm_open_interest_5m: official_qualified, blocking_gaps, source_blocked=false, release_blocked=true, samples=10
binance_usdm_funding_realized: official_qualified, blocking_gaps, source_blocked=false, release_blocked=true, samples=10
binance_usdm_funding_indicative_1h: official_qualified, blocking_gaps, source_blocked=false, release_blocked=true, samples=20
binance_usdm_mark_index_basis_1h: official_qualified, blocking_gaps, source_blocked=false, release_blocked=true, samples=60
binance_usdm_liquidation_observed_daily: secondary_qualified, typed_gaps, source_blocked=false, release_blocked=false, samples=686
binance_usdm_cost_calibration: official_qualified, blocking_gaps, source_blocked=false, release_blocked=true, samples=6
binance_usdm_coverage_gap: derived_excluded, not_applicable, source_blocked=false, release_blocked=false, samples=0
binance_usdm_harmonic_bundle: derived_excluded, not_applicable, source_blocked=false, release_blocked=false, samples=0
```

Manifest detail identity:

```text
path=evidence/manifests/sha256/1d21de4d68fb0dfd330dc480a0d27ddf2216c3b7d5e93b13ff70ea26230f968d.jsonl.gz
compressed_sha256=576b3d7b03ff16fd492c5a9382e35f65e54d73ef3996c3a7fe5c6e6ba49b0fb4
compressed_bytes=11294610
uncompressed_sha256=1d21de4d68fb0dfd330dc480a0d27ddf2216c3b7d5e93b13ff70ea26230f968d
uncompressed_bytes=466713055
records: row=733203 collision=0 rejection=0 raw_validation_pending_key=733130 total_records=1466334
object_count=733203
consumable_object_count=73
```

The manifest-detail gzip exists and rehashes to the report's compressed identity:

```text
11294610 / 576b3d7b03ff16fd492c5a9382e35f65e54d73ef3996c3a7fe5c6e6ba49b0fb4  data/cex002_qualify/evidence/manifests/sha256/1d21de4d68fb0dfd330dc480a0d27ddf2216c3b7d5e93b13ff70ea26230f968d.jsonl.gz
```

Gate 2 storage remains unproved by the report:

```text
gate2_storage_state=unknown
selected_raw_bytes=7833966625
cost_sample_bytes=12522974218
projected_new_bytes=20351715427
available_bytes=166896631808
total_required_bytes=null
unknown_components=[normalized_catalog_bytes, temporary_high_water_bytes, operating_reserve_bytes]
```

## Sample and reservation after-proof

Sample accounting:

```text
sample_count=106
acquired_count=0
reused_count=106
failed_count=0
total_sample_bytes=1116273
acquired_bytes=0
reused_bytes=1116273
```

The raw tree identity stayed unchanged, proving no out-of-plan raw identity and no
unapproved bulk acquisition:

```text
8577f80bc794dab4fe7b98aa8566118aa4ccac7a05c603aed2914b17ec5889f1 files=270 bytes=1016247871 path=data/cex002_qualify/raw
```

The two formerly reserved cost objects settled:

```text
data/futures/um/daily/bookTicker/LTCBUSD/LTCBUSD-bookTicker-2023-08-25.zip
  reused_existing=true byte_size=317
  cost_priceable=false observation=typed_unavailable_cost_observation
  quote_states={ask_only:0,bid_only:0,empty:1,two_sided:0}

data/futures/um/daily/bookTicker/XRPUSDC/XRPUSDC-bookTicker-2024-01-04.zip
  reused_existing=true byte_size=203536
  cost_priceable=true observation=priceable_two_sided_quotes_observed
  quote_states={ask_only:0,bid_only:4,empty:0,two_sided:12974}
```

Amendment ledger after execution:

```text
charges=84
reservations=0
charge_count=84
charged_bytes=1049324
planned_total_bytes=1049324
transferred_total_bytes=1049324
reservation_count=0
state_sha256=cae886a6486f48af39e7e51a5e93651971dc4f14f846d5f60f0c09f3dc114e61
```

## Artifact and tree after-proof

After-execution artifact identities:

```text
13559766 / bf01f88976e2ac3d224e843f340de726f5c8c337ba56a50f9e3c6f75c4d6f227  research/sprint_004/62_CEX002_GATE1_SOURCE_PROCUREMENT.json
426276 / 522271238e38a3652f9521b236981544782e02459450703f21e9ef344d476fa6  data/cex002_qualify/cex002_sample_plan_lock.json
26103 / 259a1bfe274f402207dbd15e6e582fb4619bed62ddca5f606ea470755084b1b0  data/cex002_qualify/cex002_amendment_ledger.json
777 / 47341a9ca2c60caf73485fb9bac40c6526cb35a13471e4545cd9cdcee6e227f6  data/cex002_qualify/cex002_budget_ledger.json
487815 / cc35a5c2c1fd72904d0d6a899565a763c89a38bb1295275e589e4d92be67eaff  data/cex002_qualify/cex002_qualification_progress.json
13737 / a9c77e465972a5ab59960519f5e4fab12a63c4767747eaee22e4d12d429b0a24  data/cex002_qualify/cex002_retry_journal.json
51124 / 02f8e435b18643586ff6e778bfd85cffd0136457b5dcf8466f5a24c35e2f2d18  data/cex002_qualify/cex002_sample_plan.json
33206753 / d584e22aaaa9414b06dbe13bc24dda0b01ed48e37bdf66f5b42f90865959bf9a  data/cex002_qualify/cex002_listing_checkpoint.json
99357 / e520f0f072730f566d027342ddc7e09f7b690ab80e76acbd40756759f13add1f  data/cex002_qualify/cex002_official_contract_metadata.json
13944475 / 53f8f93379cb55d66b6de062f1a6a85f4c9dd318f5b41cc047bff2f5feeaaf51  data/cex002_qualify/evidence/prior_reports/sha256/53f8f93379cb55d66b6de062f1a6a85f4c9dd318f5b41cc047bff2f5feeaaf51.json
425308 / 8fda3c7db11173dafa122114667622f501b62ecf05f12cdf796897d5af0942bc  data/cex002_qualify/evidence/locks/sha256/8fda3c7db11173dafa122114667622f501b62ecf05f12cdf796897d5af0942bc.json
25223 / 2a4c4db6e14350d6814b6f72a3caa1357659cd064a13fd2edeb84a2896223c8c  data/cex002_qualify/evidence/ledgers/sha256/2a4c4db6e14350d6814b6f72a3caa1357659cd064a13fd2edeb84a2896223c8c.json
```

The corrected lock is byte-identical to the pre-snapshot and still carries two source
receipts with latest code/config digest
`da33197203e0c9651dc84f42e6e2ce26867339cebe4c68286a00639046c08258`. The preserved prior
report, prior lock, prior amendment ledger, legacy ledger, retry journal, sample plan,
listing checkpoint, and raw/list/Coinalyze/cache-independent trees remain byte-identical.

Post-execution deterministic tree identities:

```text
8577f80bc794dab4fe7b98aa8566118aa4ccac7a05c603aed2914b17ec5889f1 files=270 bytes=1016247871 path=data/cex002_qualify/raw
d97420a075224d6639e894a5c98e848dbb4abccc581f0d6cf5fa356054b470bf files=41045 bytes=5158280401 path=data/cex002_qualify/list_cache
aba901aaf7ab1476f79d83c36ab38f1ecf7f2300e5411d0d6ea52d9d62aa5770 files=17 bytes=15087255 path=data/cex002_qualify/fapi_cache
cacb115bbb7dab1ce6a7d97870e1e3d3f9e615670f3ec68d06d4d5ff7f92b9ba files=6 bytes=6465528 path=data/cex002_qualify/fapi_snapshots
5bf18914908474688bdfeea6563e334f8742b7406ee5c2b5b781823865440eec files=7 bytes=3144369 path=data/cex002_qualify/coinalyze_cache
1c8aea98f13b88980da8ed8cc57b974310414142c7db38bc001ad5f6a080d5a1 files=4 bytes=1104537857 path=data/cex002_qualify/evidence/prior_reports
4aa6732dbcebbfd83aca8acd0b6a4c60e2d3fd9dc994217bab42dbe9c8411135 files=3 bytes=33875501 path=data/cex002_qualify/evidence/manifests
2bbeeaeaa1cb5b0d3b6913279e1cc65e1a9711cd0e9464b69309d14846e94af2 files=2 bytes=807163 path=data/cex002_qualify/evidence/locks
e64b9308f13f8165f6c8672059896982372a2c50cfe2ea1f6ffbfe151ff6a11d files=1 bytes=25223 path=data/cex002_qualify/evidence/ledgers
```

Expected mutations were limited to the report, progress checkpoint, amendment ledger,
official metadata/FAPI cache, prior-report evidence tree, and manifest evidence tree.
Data/evidence paths are intentionally unstaged except for the tracked report 62.

Available bytes after execution:

```text
166,868,078,592
```

## Disposition

The one authorized corrected ordinary qualification run exited `0` and produced a changed
valid report claiming `gate_status=QUALIFIED`. Gate 1 is not accepted by Hermes; reviewer
inspection of this record and report 62 remains mandatory.

CEX-002 remains `IN_PROGRESS`; Gate 1 has not passed; next ticket remains `NONE`.

Next required actor: Lead Quantitative Finance Researcher/Engineer - inspect record 178.
