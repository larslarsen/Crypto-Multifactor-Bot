# CEX-002 Focused Test Integration and Version-4 Candidate

Date: 2026-08-21
Author: Jr Dev - Hermes
Governing review: `research/sprint_004/143_CEX002_FOCUSED_TEST_SOURCE_ACCEPTANCE.md`

## 1. Focused test integration

Hermes established `HEAD == origin/main == c213272fe31c3521d9b2311e46d9aa984c6c9e19`
at the review-143 publication commit before staging.

Accepted identities re-proved before staging:

| Path | SHA-256 |
|---|---|
| `tests/acquisition/test_binance_usdm_harmonic_qualification.py` | `186eccc22df2eb8f49f8f004141b6be7efdae15080afefa0675cfbd26e7a3fdd` |
| `src/cryptofactors/acquisition/binance_usdm_harmonic_qualification.py` | `2f9647d8c41dd69e3fce79889d889b54beb3c8742d8d7ef24d57803cdd2443b1` |
| `scripts/research/qualify_binance_usdm_harmonic_sources.py` | `8c455659af3a4ac13184b2ba4034dbeb1308a78e0834a2eed970159d6e577cbc` |
| `src/source_audit/download.py` | `f231930f743f4b2f415dd84a96ec3c1ec3b1c1efab5deb7536db57fce5473fa5` |
| `tests/test_download_atomicity.py` | `30388dba0568912b7bbe3f83c5454de89cd8cf5cd1288f260d30cfda0bd8d587` |

The fixture directory diff for
`tests/acquisition/fixtures/binance_usdm_harmonic_qualification/` was empty. The CEX test
file retained 261 uniquely named `test_` functions. The accepted compact report re-proved
at 17,349,108 bytes and SHA-256
`e51ef2735c4937cf61cc614836478ee053c89f8100d5e4193a22e665f651fcd9`.

Hermes staged exactly `tests/acquisition/test_binance_usdm_harmonic_qualification.py` and
committed:

`56dc47128437f4db303e78629ceeccb1ca894d44`

Commit message:

`CEX-002: integrate focused delivery test correction`

After push:

`HEAD == origin/main == 56dc47128437f4db303e78629ceeccb1ca894d44`

The index was empty. Existing unrelated dirty paths remained unstaged and untouched. No
source or test edit was made after integration.

## 2. Focused commands

Review 143 required the full stop-on-first-failure command sequence. All five commands
returned exit 0, so report preservation and the one candidate were authorized.

| Step | Command | Exit | Observed output |
|---|---|---:|---|
| C1 | `.venv/bin/python -m pytest tests/acquisition/test_binance_usdm_harmonic_qualification.py -q --tb=short` | 0 | progress reached `[100%]`; no collected/pass count printed under this invocation |
| C2 | `.venv/bin/python -m pytest tests/test_download_atomicity.py -q --tb=short` | 0 | `.................. [100%]` |
| C3 | `.venv/bin/python -m ruff check src/cryptofactors/acquisition/binance_usdm_harmonic_qualification.py scripts/research/qualify_binance_usdm_harmonic_sources.py src/source_audit/download.py tests/acquisition/test_binance_usdm_harmonic_qualification.py tests/test_download_atomicity.py` | 0 | `All checks passed!` |
| C4 | `python3 scripts/check_repo_control.py` | 0 | `Repo control check: PASS` |
| C5 | `git show --check --oneline --no-renames HEAD` | 0 | `56dc471 CEX-002: integrate focused delivery test correction` |

## 3. Report preservation

After all five focused commands passed, Hermes preserved the accepted compact report at:

`data/cex002_qualify/evidence/prior_reports/sha256/e51ef2735c4937cf61cc614836478ee053c89f8100d5e4193a22e665f651fcd9.json`

Procedure and proof:

- source report before preservation: 17,349,108 bytes, SHA-256
  `e51ef2735c4937cf61cc614836478ee053c89f8100d5e4193a22e665f651fcd9`;
- existing destination was absent;
- copied to a sibling temporary file with `cp --reflink=never`, never a hard link;
- temporary file re-proved at 17,349,108 bytes and the same SHA-256;
- atomically renamed to the content-addressed destination;
- final destination re-proved at 17,349,108 bytes and the same SHA-256.

The previously preserved monolith also re-proved at 1,059,297,547 bytes and SHA-256
`46d1980ecf384874e45c4c31f142c16efc5472ef63231e9456e264f3e94ef691`.

## 4. Before snapshot

No separate candidate process was running; the process scan matched only the scan command
itself.

Before candidate:

- `HEAD == origin/main == 56dc47128437f4db303e78629ceeccb1ca894d44`;
- index empty;
- plan lock: `data/cex002_qualify/cex002_sample_plan_lock.json`, 381,855 bytes, SHA-256
  `e04a5ce2f2513cc8a0f4e6698dcbf9d43c5a7bec0295021ca5d431ff886f0d84`;
- legacy budget ledger: 777 bytes, SHA-256
  `47341a9ca2c60caf73485fb9bac40c6526cb35a13471e4545cd9cdcee6e227f6`;
- listing checkpoint: 33,206,753 bytes, SHA-256
  `d584e22aaaa9414b06dbe13bc24dda0b01ed48e37bdf66f5b42f90865959bf9a`;
- retry journal: 12,977 bytes, SHA-256
  `ff4edb0362f838765c6427c4247d9c9ceb44bea0e011210266383a56feb1c940`;
- progress file: 299,571 bytes, SHA-256
  `5c85bbf09e6d6c3c9183f82daf5ac09567410cce62f1f3c6b2026cb9d59a2eb1`;
- amendment ledger absent;
- retained raw tree: 186 files, 1,015,198,547 bytes, listing digest
  `ec06dcad4f761ff8564460d4921d026d2c35dd3ce38b44237f40194ceadf96dc`;
- list cache: 40,961 files, 5,158,272,575 bytes, listing digest
  `958407092a2f7f171c958762524e970b182dbe291cb7199b18f1b3ac1ae74d42`;
- FAPI cache: 10 files, 10,774,707 bytes, listing digest
  `020322270ba0b3ac4e496f9d0ea10653a425f3557abd94237b27a32360cd4639`;
- Coinalyze cache: 7 files, 3,144,369 bytes, listing digest
  `4994f246b9ed7c18aff9ca88e7175898a50fb442907ff9e889eb8bb31a44e393`;
- manifest-detail root: 1 file, 11,288,256 bytes;
- available bytes: 173,040,644,096.

## 5. Candidate execution

`.env` was loaded only into the process environment. Hermes made exactly one foreground
invocation with the review-143 command. The command started at
2026-08-21T17:22:11-07:00 and ended at 2026-08-21T17:31:30-07:00.

Exit/status: `2`.

Terminal console summary:

```text
Qualification report written to research/sprint_004/62_CEX002_GATE1_SOURCE_PROCUREMENT.json
manifest_detail: path=evidence/manifests/sha256/d9be584d7a1eecd43482ea1a05a0d9dd8cd681970c4ec5ff225740a28f27a5bf.jsonl.gz uncompressed_sha256=d9be584d7a1eecd43482ea1a05a0d9dd8cd681970c4ec5ff225740a28f27a5bf uncompressed_bytes=466717014 compressed_sha256=8abf72fa22c6714051c2b451bfd27e17b6c84a65b7e476be63bc21f09f265945 compressed_bytes=11288256 records={'row': 733203, 'collision': 0, 'rejection': 0, 'raw_validation_pending_key': 733191, 'total_records': 1466395} reused_existing=True
gate_status=BLOCKED accepted=False symbols=1004 blocked=['binance_usdm_perpetual_membership', 'binance_usdm_bar_1h', 'binance_usdm_open_interest_5m', 'binance_usdm_funding_realized', 'binance_usdm_funding_indicative_1h', 'binance_usdm_mark_index_basis_1h', 'binance_usdm_cost_calibration']
membership: basis=confirmed_perpetual_membership confirmed=771 unresolved=0 classes={'confirmed_perpetual': 771, 'delivery_non_perpetual': 4, 'official_archive_settlement_alias': 17, 'reviewed_delivery_non_perpetual': 46, 'tradifi_perpetual': 170}
candidate_plan: state=candidate_unmigrated version=4 prior_version=2 plan_digest=2fb0e47a3666f0e87b35dd7fdd6ea26aa352e34acf8dfd5debf590409aecbbef envelope_digest=be63989bd4d3d40c95c7ca405eae7558ce0ef997a2289892d14ed8d773d4cbfe migration_authorized=False download_authorized=False
ERROR: incomplete product matrix is refused
CANDIDATE_STATUS=2
CANDIDATE_END=2026-08-21T17:31:30-07:00
```

Status 2 is terminal evidence. No retry or second candidate invocation was run.

## 6. After snapshot and deltas

After candidate:

- report 62: 13,946,727 bytes, SHA-256
  `f26abbc577307e5dcef693ec159fa65d1373d7b03c2be0eb6b926e5b09f97406`;
- manifest detail: 11,288,256 bytes, compressed SHA-256
  `8abf72fa22c6714051c2b451bfd27e17b6c84a65b7e476be63bc21f09f265945`;
- plan lock unchanged at SHA-256
  `e04a5ce2f2513cc8a0f4e6698dcbf9d43c5a7bec0295021ca5d431ff886f0d84`;
- legacy budget ledger unchanged at SHA-256
  `47341a9ca2c60caf73485fb9bac40c6526cb35a13471e4545cd9cdcee6e227f6`;
- listing checkpoint unchanged at SHA-256
  `d584e22aaaa9414b06dbe13bc24dda0b01ed48e37bdf66f5b42f90865959bf9a`;
- retry journal unchanged at SHA-256
  `ff4edb0362f838765c6427c4247d9c9ceb44bea0e011210266383a56feb1c940`;
- progress file advanced to SHA-256
  `b60fe7b6d805f9cc14a67f1256978a742556b94949c3a74b89e1cf597d02ca7f`;
- retained raw tree unchanged at 186 files / 1,015,198,547 bytes / digest
  `ec06dcad4f761ff8564460d4921d026d2c35dd3ce38b44237f40194ceadf96dc`;
- list cache unchanged at 40,961 files / 5,158,272,575 bytes / digest
  `958407092a2f7f171c958762524e970b182dbe291cb7199b18f1b3ac1ae74d42`;
- FAPI cache advanced to 14 files / 11,854,509 bytes / digest
  `f86e429cd2aea44647aa9be3dc4d4e6195c9709a960f5b535e808a8e40b0bf82`;
- Coinalyze cache unchanged at 7 files / 3,144,369 bytes / digest
  `4994f246b9ed7c18aff9ca88e7175898a50fb442907ff9e889eb8bb31a44e393`;
- manifest-detail root remained one file / 11,288,256 bytes / digest
  `b26b4fd27fe28d4129213b05d4851fb977ee1dbe3c5ddf3f9efe69021bf31a2e`;
- available bytes: 172,678,488,064.

## 7. Report and ADR-0020 proof

The replaced report is valid JSON and remains below the compact-report ceiling.

Accepted manifest-detail validation passed through `validate_manifest_detail`, recomputing:

| Field | Value |
|---|---|
| relative path | `evidence/manifests/sha256/d9be584d7a1eecd43482ea1a05a0d9dd8cd681970c4ec5ff225740a28f27a5bf.jsonl.gz` |
| uncompressed SHA-256 / bytes | `d9be584d7a1eecd43482ea1a05a0d9dd8cd681970c4ec5ff225740a28f27a5bf` / 466,717,014 |
| compressed SHA-256 / bytes | `8abf72fa22c6714051c2b451bfd27e17b6c84a65b7e476be63bc21f09f265945` / 11,288,256 |
| records | row 733,203; collision 0; rejection 0; raw_validation_pending_key 733,191; total 1,466,395 |
| selected compressed raw bytes | 7,833,966,625 |
| consumable objects | 12 |

ADR-0020 authority proof:

- delivery identities: 46 total, 36 direct, 10 reviewed archive;
- settlement aliases: 17 aliases to 16 bases;
- delivery table SHA-256:
  `678d07e0679b0e116a372a333c3c33f74f5e421dadba393cb9516e56ae8b9a01`;
- alias table SHA-256:
  `e9837ee2ac0711e41981e27979532be5095d61f04fb82442919c9f301f5998f8`;
- resolved delivery identities: 46;
- resolved settlement aliases: 17;
- mismatches: `[]`;
- no unresolved archive names remain.

Delivery-price evidence:

- `BTCBUSD`: retained official response SHA-256
  `4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945`,
  0 records; request params `{"pair": "BTCBUSD"}`;
- `BTCUSDT`: retained official response SHA-256
  `4c11fe09afdd8a46e6496440d1c99ba7ac325326732b3dc0fda327044f02d8c4`,
  18 records; request params `{"pair": "BTCUSDT"}`;
- `ETHUSDT`: retained official response SHA-256
  `ba2ada67b97e3e8a677f832560a39865078b20ea21abee1caf718171bae8accb`,
  18 records; request params `{"pair": "ETHUSDT"}`.

No secret-bearing request field is present in these records.

Cost proof:

- complete cost manifest: 3,144 objects, 12,522,974,218 compressed bytes, digest
  `04842ff6b9b58280b3ec2ea2644b3d44769be62d460bef785262cd4dd65cac57`,
  version `cex002_complete_cost_manifest_v1`;
- cost-source selector: `three_era_smallest_positive_cost_source_v1`;
- cost-source families: `daily/bookTicker`, `daily/bookDepth`;
- cost-source strata: `early`, `middle`, `recent`;
- bounded cost-source object count: 6;
- validation version: `cex002_cost_source_validation_v1`;
- validation summaries remain pending because candidate-only mode keeps `samples` empty;
- Gate-1 allowance remains 268,435,456 bytes; planned new bytes are 1,049,324; remaining
  allowance is 267,386,132; no migration or download is authorized.

Candidate proof:

- candidate version: 4;
- prior lock version: 2;
- prior versions: 0, 1, 2;
- superseded version-3 plan digest:
  `0a1c358c8fee3df35d1049424502b11e38c0084592a03ab6f9de99b8a0078593`;
- superseded version-3 envelope digest:
  `a14018c27d8e00d3f59d4181d7da546ca99d43f5625c34d39cb07398859605c3`;
- version-4 plan digest:
  `2fb0e47a3666f0e87b35dd7fdd6ea26aa352e34acf8dfd5debf590409aecbbef`;
- version-4 envelope digest:
  `be63989bd4d3d40c95c7ca405eae7558ce0ef997a2289892d14ed8d773d4cbfe`;
- complete-cost digest bound into candidate:
  `04842ff6b9b58280b3ec2ea2644b3d44769be62d460bef785262cd4dd65cac57`;
- `migration_authorized=false`;
- `download_authorized=false`;
- `samples=[]`;
- assertions: prior lock bytes unchanged, legacy ledger bytes unchanged, no migration,
  no download, no public relock switch, and legacy ledger not charged again.

## 8. Terminal state

`gate_status=BLOCKED` and `accepted=false`. Seven source products remain blocked:

- `binance_usdm_perpetual_membership`
- `binance_usdm_bar_1h`
- `binance_usdm_open_interest_5m`
- `binance_usdm_funding_realized`
- `binance_usdm_funding_indicative_1h`
- `binance_usdm_mark_index_basis_1h`
- `binance_usdm_cost_calibration`

The product matrix is still incomplete. Gate 1 has not passed. No plan migration, sample
acquisition, Gate 2, normalization, catalog publication, Nautilus work, Harmonic Trader
work, payoff analysis, PAPER, LIVE, paid source, Git LFS, external artifact service, scope
reduction, report truncation, unrelated-ticket work, or next-ticket work is authorized.

## 9. Publication

This publication stages exactly:

- `docs/handoff/CURRENT_TASK.md`;
- `research/sprint_004/62_CEX002_GATE1_SOURCE_PROCUREMENT.json`;
- `research/sprint_004/144_CEX002_FOCUSED_TEST_INTEGRATION_AND_CANDIDATE.md`;
- `tickets/CEX-002.md`.

Preserved reports and manifest detail remain ignored evidence and are not staged.
