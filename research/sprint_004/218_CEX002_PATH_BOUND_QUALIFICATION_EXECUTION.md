# CEX-002 Path-Bound Qualification Execution

**Date:** 2026-08-22
**Actor:** Jr Dev - Hermes
**Reviewer authorization:** `research/sprint_004/217_CEX002_PATH_BOUND_QUALIFICATION_AUTHORIZATION.md`
**Decision status:** execution published for reviewer inspection
**Gate 1:** corrected ordinary qualification report published, reviewer acceptance pending
**Gate 2:** not accepted

## Scope

Hermes executed only review 217's authorized work: exact preproof, one network-enabled
ordinary qualification invocation, this record, the changed terminal report, and the two
control updates.

No retry, second qualification, sizing, bulk acquisition, normalization, catalog
publication, NautilusTrader, Harmonic Trader, payoff, PAPER, LIVE, paid source, reduced
scope, pytest, Ruff, or next-ticket work was run.

## Pre-execution proof

`HEAD == origin/main` before execution:

```text
320d795b346eb30316591f6a6f57bdcb4bb609cf
320d795b346eb30316591f6a6f57bdcb4bb609cf
```

No qualification process was running:

```text
pgrep -af '[q]ualify_binance_usdm_harmonic_sources|[b]inance_usdm_harmonic_qualification'
exit status: 1
stdout: empty
```

Required pre-state identities matched review 217:

| Artifact | Bytes | SHA-256 |
|---|---:|---|
| qualification production | 512,435 | `2f88ad6e7cfc531fefe3d9c7a9ddbc830741687e93c51450fc826062dffb2c74` |
| qualification CLI | 18,571 | `473185ca946dcc37d506d8891e8f955708ff80c976a586967762c1294956d28f` |
| qualification tests | 460,268 | `e4bd0203668a4488fe56ba4efede53696d908a0a68a227d005e3420badc29dea` |
| live report 62 | 13,559,766 | `bf01f88976e2ac3d224e843f340de726f5c8c337ba56a50f9e3c6f75c4d6f227` |
| live manifest detail gzip | 11,294,610 | `576b3d7b03ff16fd492c5a9382e35f65e54d73ef3996c3a7fe5c6e6ba49b0fb4` |
| live manifest detail uncompressed | 466,713,055 | `1d21de4d68fb0dfd330dc480a0d27ddf2216c3b7d5e93b13ff70ea26230f968d` |
| live version-4 lock | 428,097 | `6cbd044adf4ace577ff8899b2825723e8c0ae99d1fe3c855f2783ce54d7b722e` |
| live amendment ledger | 26,677 | `2d41fbf009d9803ca5bda05c3a11d75dafe505a1397756e5fafefeb2d1cb90bf` |
| legacy budget ledger | 777 | `47341a9ca2c60caf73485fb9bac40c6526cb35a13471e4545cd9cdcee6e227f6` |
| live sample checkpoint / progress | 487,815 | `cc35a5c2c1fd72904d0d6a899565a763c89a38bb1295275e589e4d92be67eaff` |
| retry journal | 13,737 | `a9c77e465972a5ab59960519f5e4fab12a63c4767747eaee22e4d12d429b0a24` |
| sample plan | 51,124 | `02f8e435b18643586ff6e778bfd85cffd0136457b5dcf8466f5a24c35e2f2d18` |
| listing checkpoint | 33,206,753 | `d584e22aaaa9414b06dbe13bc24dda0b01ed48e37bdf66f5b42f90865959bf9a` |
| official metadata | 99,357 | `e520f0f072730f566d027342ddc7e09f7b690ab80e76acbd40756759f13add1f` |

The test source contained exactly 315 `def test_` functions.

The lock and amendment ledger carried the same three-receipt binding. The final receipt
bound qualification production SHA-256
`2f88ad6e7cfc531fefe3d9c7a9ddbc830741687e93c51450fc826062dffb2c74`
and code/config digest
`86ff0eb0ee5fa379855745aedb41bb8442b0a244a8c5a740665acc735fba28fb`.

Transition-preserved evidence rehashed to its content-addressed name before execution:

| Evidence object | Bytes | SHA-256 |
|---|---:|---|
| prior report | 13,559,766 | `bf01f88976e2ac3d224e843f340de726f5c8c337ba56a50f9e3c6f75c4d6f227` |
| prior checkpoint | 487,815 | `cc35a5c2c1fd72904d0d6a899565a763c89a38bb1295275e589e4d92be67eaff` |
| prior lock | 426,276 | `522271238e38a3652f9521b236981544782e02459450703f21e9ef344d476fa6` |
| prior ledger | 26,103 | `259a1bfe274f402207dbd15e6e582fb4619bed62ddca5f606ea470755084b1b0` |

Before execution, available bytes on the filesystem containing `data/cex002_qualify` were
157,881,167,872. Store file counts were: manifest evidence 3, all evidence 14, retained
raw tree 270, and full `data/cex002_qualify` tree 41,369.

## Execution command and transcript

Hermes obtained network-enabled execution permission and ran the authorized foreground
ordinary qualification once. The child process loaded `.env`; no preliminary restricted
sandbox attempt was consumed.

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
start_utc=2026-08-22T22:45:13Z
listing checkpoint bootstrap: claimed=0 checksum_blobs=270 skipped_already_bound=40771 unclaimed=0
Qualification report written to research/sprint_004/62_CEX002_GATE1_SOURCE_PROCUREMENT.json
manifest_detail: path=evidence/manifests/sha256/d6c1fac650aaf16d88750da2a40d837f543d0c5fc88c73d463753a576d5bdd17.jsonl.gz uncompressed_sha256=d6c1fac650aaf16d88750da2a40d837f543d0c5fc88c73d463753a576d5bdd17 uncompressed_bytes=466714158 compressed_sha256=64d0f74b8e4696c98d0f96423185fd961aba6c63348d12425e3ec364b888f113 compressed_bytes=11292635 records={'row': 733203, 'collision': 0, 'rejection': 0, 'raw_validation_pending_key': 733147, 'total_records': 1466351} reused_existing=True
gate1_source_blockers:
release_blockers: binance_usdm_bar_1h,binance_usdm_trade_flow_1h,binance_usdm_open_interest_5m,binance_usdm_funding_realized,binance_usdm_funding_indicative_1h,binance_usdm_mark_index_basis_1h,binance_usdm_cost_calibration
gate_status=QUALIFIED accepted=True symbols=1004 blocked=[]
sample_plan: planned_new_bytes=1049324 budget=268435456 retained_bytes=44642 budget_blocked=0
plan_lock: version=4 state=locked plan_digest=2fb0e47a3666f0e87b35dd7fdd6ea26aa352e34acf8dfd5debf590409aecbbef superseded=[0, 1, 2]
budget: charged=1049324 spent_range=[1049324,1049324] remaining=267386132 reserved=0 legacy_state=resolved breach_state=none
membership: basis=confirmed_perpetual_membership confirmed=771 unresolved=0 classes={'confirmed_perpetual': 771, 'delivery_non_perpetual': 4, 'official_archive_settlement_alias': 17, 'reviewed_delivery_non_perpetual': 46, 'tradifi_perpetual': 170}
gate2_storage: state=unknown selected_raw_bytes=7833966625 cost_sample_bytes=12522974218 projected_new_bytes=20351715427 available_bytes=157647167488 total_required_bytes=None unknown_components=['normalized_catalog_bytes', 'temporary_high_water_bytes', 'operating_reserve_bytes']
candidate_plan: state=not_constructed version=4 prior_version=None plan_digest=None envelope_digest=None migration_authorized=False download_authorized=False
holdout: id=c842f813839e1dda375b351da0f693c54bcf932e33eb6e3394aba860c12346e2 boundary_utc=2026-08-21T16:19:08.994166+00:00 stream_collector=False
listing_checkpoint: reused=39812 fetched=0 unclaimed=0 serializations=1 | workers=8 clients=1/1 retries=0
end_utc=2026-08-22T22:55:09Z
elapsed_seconds=596
qualification_status=0
```

The command exited status 0. This ended the execution authorization; Hermes ran no second
qualification.

## Terminal report

The changed terminal report is
`research/sprint_004/62_CEX002_GATE1_SOURCE_PROCUREMENT.json`.

| Artifact | Bytes | SHA-256 |
|---|---:|---|
| report 62 | 13,745,360 | `f27b2ba7e6eff3a8b1385d985c49ee64ef60a394737b1246130d0f37b9015f09` |
| manifest detail gzip | 11,292,635 | `64d0f74b8e4696c98d0f96423185fd961aba6c63348d12425e3ec364b888f113` |
| manifest detail uncompressed | 466,714,158 | `d6c1fac650aaf16d88750da2a40d837f543d0c5fc88c73d463753a576d5bdd17` |

Report facts:

- `ticket`: `CEX-002`;
- `gate`: `gate_1_source_procurement`;
- `gate_status`: `QUALIFIED`;
- `accepted`: `true`;
- `generated_at`: `2026-08-22T22:45:15.097674+00:00`;
- discovered symbols: 1,004;
- confirmed perpetual membership: 771;
- unresolved membership: 0;
- source blockers: none;
- blocked products: none;
- release blockers: `binance_usdm_bar_1h`, `binance_usdm_trade_flow_1h`,
  `binance_usdm_open_interest_5m`, `binance_usdm_funding_realized`,
  `binance_usdm_funding_indicative_1h`, `binance_usdm_mark_index_basis_1h`,
  `binance_usdm_cost_calibration`.

Product matrix:

| Product | Source gate | Coverage state | Samples | Release blocked |
|---|---:|---|---:|---:|
| `binance_usdm_perpetual_membership` | true | complete | 0 | false |
| `binance_usdm_bar_1h` | true | blocking_gaps | 20 | true |
| `binance_usdm_trade_flow_1h` | false | blocking_gaps | 0 | true |
| `binance_usdm_open_interest_5m` | true | blocking_gaps | 10 | true |
| `binance_usdm_funding_realized` | true | blocking_gaps | 10 | true |
| `binance_usdm_funding_indicative_1h` | true | blocking_gaps | 20 | true |
| `binance_usdm_mark_index_basis_1h` | true | blocking_gaps | 60 | true |
| `binance_usdm_liquidation_observed_daily` | true | typed_gaps | 686 | false |
| `binance_usdm_cost_calibration` | true | blocking_gaps | 6 | true |
| `binance_usdm_coverage_gap` | false | not_applicable | 0 | false |
| `binance_usdm_harmonic_bundle` | false | not_applicable | 0 | false |

ADR-0022 retained decomposition matched the review-217 expectation:

- retained valid requirement keys: 73;
- retained verified credit objects: 73;
- retained verified credit bytes: 5,225,416;
- selected-manifest consumable objects: 56;
- retained complete-cost keys: 17;
- rejected ambiguous retained rows: 176;
- unverified retained objects: 0.

The report states that a basename-only sidecar binds a full key only when the complete
frozen candidate domain maps that basename to exactly one key. Ambiguous basename-only
retained rows were rejected for consumability, reuse credit, and source evidence; their
prior bytes remain lineage evidence only.

Sample/accounting facts:

- `samples` entries: 106;
- checksum-matching samples: 106;
- reused existing sample entries: 106;
- new downloaded sample entries in the report list: 0;
- sample-plan unique new objects: 84;
- sample-plan unique retained objects: 12;
- sample-plan planned new bytes: 1,049,324;
- sample-plan retained bytes: 44,642;
- sample-plan budget blocked entries: 0;
- budget charged/settled bytes: 1,049,324;
- settled object count: 84;
- remaining allowance bytes: 267,386,132;
- reserved bytes/objects: 0 / 0;
- breach state: `none`;
- legacy state: `resolved`.

Gate-2 storage remains unknown in the report:

- selected raw bytes: 7,833,966,625;
- complete cost sample bytes: 12,522,974,218;
- selected plus cost compressed raw bytes: 20,356,940,843;
- physical object count: 736,347;
- normalized catalog bytes: `unknown`;
- temporary high-water bytes: `unknown`;
- operating reserve bytes: `unknown`;
- total sufficiency: `unknown`.

Candidate plan remains not constructed: `plan_version=4`, `migration_authorized=false`,
and `download_authorized=false`.

## Post-execution artifact proof

After execution:

| Artifact | Bytes | SHA-256 |
|---|---:|---|
| live version-4 lock | 428,097 | `6cbd044adf4ace577ff8899b2825723e8c0ae99d1fe3c855f2783ce54d7b722e` |
| live amendment ledger | 26,677 | `2d41fbf009d9803ca5bda05c3a11d75dafe505a1397756e5fafefeb2d1cb90bf` |
| retry journal | 13,737 | `a9c77e465972a5ab59960519f5e4fab12a63c4767747eaee22e4d12d429b0a24` |
| legacy budget ledger | 777 | `47341a9ca2c60caf73485fb9bac40c6526cb35a13471e4545cd9cdcee6e227f6` |
| live sample checkpoint / progress | 487,815 | `cc8e02389d182e6d76d00b913503d95f72a352d883c50ffd81dd3c49df157b2f` |
| sample plan | 51,124 | `02f8e435b18643586ff6e778bfd85cffd0136457b5dcf8466f5a24c35e2f2d18` |
| listing checkpoint | 33,206,753 | `d584e22aaaa9414b06dbe13bc24dda0b01ed48e37bdf66f5b42f90865959bf9a` |
| official metadata | 99,774 | `7aaea96ecd4cb13c83b8b19930a6e1ef0fcf2b49de841e1fa26878d6dd7f5b42` |

Transition-preserved evidence remained byte-identical:

| Evidence object | Bytes | SHA-256 |
|---|---:|---|
| prior report | 13,559,766 | `bf01f88976e2ac3d224e843f340de726f5c8c337ba56a50f9e3c6f75c4d6f227` |
| prior checkpoint | 487,815 | `cc35a5c2c1fd72904d0d6a899565a763c89a38bb1295275e589e4d92be67eaff` |
| prior lock | 426,276 | `522271238e38a3652f9521b236981544782e02459450703f21e9ef344d476fa6` |
| prior ledger | 26,103 | `259a1bfe274f402207dbd15e6e582fb4619bed62ddca5f606ea470755084b1b0` |

The final live lock and amendment ledger still carry the same three-receipt binding,
including production SHA-256
`2f88ad6e7cfc531fefe3d9c7a9ddbc830741687e93c51450fc826062dffb2c74`
and code/config digest
`86ff0eb0ee5fa379855745aedb41bb8442b0a244a8c5a740665acc735fba28fb`.

After execution, available bytes on the filesystem containing `data/cex002_qualify` were
157,585,158,144. Store file counts were: manifest evidence 3, all evidence 14, retained
raw tree 270, and full `data/cex002_qualify` tree 41,372.

Observed store mutations after launch were:

| Path | Bytes | Note |
|---|---:|---|
| `data/cex002_qualify/cex002_official_contract_metadata.json` | 99,774 | refreshed official metadata |
| `data/cex002_qualify/cex002_qualification_progress.json` | 487,815 | terminal progress/checkpoint |
| `data/cex002_qualify/coinalyze_cache/a5f361ecc91ddfe2a7564f7495adbf7a8cbf75d8f7d0c180c13652592c7b1c97` | 1,449,633 | network cache |
| `data/cex002_qualify/fapi_cache/f5628c9d503d860f9579df289b99a84bf409c72e21e48555ad89b893e9974124` | 1,077,582 | network cache |
| `data/cex002_qualify/fapi_snapshots/f5628c9d503d860f9579df289b99a84bf409c72e21e48555ad89b893e9974124` | 1,077,582 | network snapshot |

The tracked report diff is:

```text
5531    2652    research/sprint_004/62_CEX002_GATE1_SOURCE_PROCUREMENT.json
```

## Publication plan

Because the command exited status 0 and produced a valid changed terminal report, Hermes
will stage exactly these paths:

- `research/sprint_004/62_CEX002_GATE1_SOURCE_PROCUREMENT.json`;
- `research/sprint_004/218_CEX002_PATH_BOUND_QUALIFICATION_EXECUTION.md`;
- `docs/handoff/CURRENT_TASK.md`;
- `tickets/CEX-002.md`.

Data/evidence files, source/tests, database sidecars, and unrelated dirty paths are not
staged.
