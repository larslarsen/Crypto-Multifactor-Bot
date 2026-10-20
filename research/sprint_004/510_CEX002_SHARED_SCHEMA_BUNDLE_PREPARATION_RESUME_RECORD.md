# CEX-002 Record 510 — Shared schema bundle preparation resume (success)

Ticket: CEX-002, IN_PROGRESS; next ticket NONE
Actor: Jr Dev — Hermes
Model: meituan/longcat-2.5-preview:free (Nous Portal), no reasoning override
Reviewer: Lead Quantitative Finance Researcher/Engineer
Governing: Review 507 `research/sprint_004/507_CEX002_SHARED_SCHEMA_SOURCE_AUTHORIZATION.md`, ADR-0038

## Outcome

The bounded preparation resume SUCCEEDED. The producer exited 0 and emitted a single
non-consumable prepared candidate. The authorized orphan disposal was performed on only the
old failed-attempt object; the 305-byte bounds marker was preserved unchanged. No catalog
row was admitted, no proof/publication or consumer run occurred, and the candidate remains
non-consumable.

## Source identity

- Source integration commit bound to the producer: `1f5629badfa0e8af6338fbeb019a5f7e60b6a324`
  (`CEX-002: share schema contracts within the fixed release metadata budget`).
- HEAD == origin/main at the start of this workflow: `5359740ee4082156125b1ecb2a51f3c33d9c805a`
  (reviewer governance commit; the five accepted blobs exist at the source commit).
- Index empty (0 staged) before the run.

Five integrated source/test hashes (unchanged, preserved):

| path | SHA-256 | lines |
| --- | --- | --- |
| src/cryptofactors/catalog/dataset/cex002_reference_release.py | fed0d0ef49eb3704be577a378dfd12eb7e6876fc41fbfe9d6507e7ef5b83fe00 | 2237 |
| tests/catalog/test_cex002_reference_release.py | 293f45157c94e9978e18aa0f6720cc68ab8c230c19524abe0cf9140a87acfc8a | 1261 |
| src/cryptofactors/ingest/binance_usdm_harmonic_bundle.py | 1c9214d088c4279cf34e78c24d97a9bc14124491c27f5575edcca67c675cb48b | 1996 |
| scripts/research/publish_binance_usdm_harmonic_bundle.py | cfb5b04f87226c9d1efbb39bbd04b634c40c7a20ddb868b8c6b3768d817b3fd9 | 102 |
| tests/ingest/test_binance_usdm_harmonic_bundle.py | 867125b2c123349abe56caa1f8c5e8ec5cc8342dc1909cb4029d123af364f2e0 | 1383 |

Hermes's accepted validation for this source (Review 507 integration acceptance, preserved,
not rerun): 162 tests passed, two-path Ruff passed, repository control PASS.

## Capacity restoration

The owner reports deleting files; the reviewer observed `df` = 148,586,504,192 bytes,
above the unchanged 34,724,877,040-byte prelaunch floor. This resolves the earlier
environmental stop only (Record 509). Observed free bytes before this resumed attempt:
148,463,267,840.

## Exact orphan disposal

Before disposal, the owned root contained exactly two regular, non-symlink files, both
authenticated:

- Old failed-attempt object:
  `data/.cex002_harmonic_bundle/.objects/89/8923a89f98eb0a570d2e4fabd227ef4d8ee02b3e6536dbdd010d23eeec53a05f`
  SHA-256 `8923a89f98eb0a570d2e4fabd227ef4d8ee02b3e6536dbdd010d23eeec53a05f`, size 13,232,150 bytes.
- Bounds marker:
  `data/.cex002_harmonic_bundle/.prepared/a918bc1271be169073d793d87461dfeb0ea6dbe5e7c8ed46793ef873a3b0308a.json`
  SHA-256 `a918bc1271be169073d793d87461dfeb0ea6dbe5e7c8ed46793ef873a3b0308a`, size 305 bytes.

No symlinked components, no other files, no live producer.

Action: `unlink` of ONLY the old object (exact full SHA as required), exit 0. The marker
and all directories were retained. Post-disposal inventory: exactly one regular file — the
unchanged 305-byte marker (SHA `a918bc1271be169073d793d87461dfeb0ea6dbe5e7c8ed46793ef873a3b0308a`,
305 bytes). No other cleanup, no directory removal, no accepted-data change.

## Producer execution

```
PYTHONPATH=src .venv/bin/python scripts/research/publish_binance_usdm_harmonic_bundle.py prepare --repo /home/lars/Crypto_Multifactor_Bot --catalog /home/lars/Crypto_Multifactor_Bot/exp003.db --code-commit 1f5629badfa0e8af6338fbeb019a5f7e60b6a324
```

Launched once via terminal background=true with notify_on_complete=true.
Native process: session `proc_2dad8d51733f`, PID 1918894, uptime 845s.
Terminal status: exited. Exit code: 0. Output (complete, 1 line):

```
8b46bebac377331a08ff1755f2a2c5362f47994939b61837542dfc9628bc9c34
```

## Candidate and manifests (success-only inspection)

- Prepared descriptor (candidate):
  `data/.cex002_harmonic_bundle/.prepared/8b46bebac377331a08ff1755f2a2c5362f47994939b61837542dfc9628bc9c34.json`
  size 11,020 bytes; document_type `cex002_harmonic_bundle_prepared_release`; `consumable=false`;
  transform `{'name': 'cex002_reference_publication', 'version': '2'}`; `catalog_commit_required=true`.
  Candidate SHA: `8b46bebac377331a08ff1755f2a2c5362f47994939b61837542dfc9628bc9c34`.
- Preserved bounds marker (unchanged, distinct from the candidate):
  `.prepared/a918bc1271be169073d793d87461dfeb0ea6dbe5e7c8ed46793ef873a3b0308a.json`,
  305 bytes, SHA `a918bc1271be169073d793d87461dfeb0ea6dbe5e7c8ed46793ef873a3b0308a`.
- Bundle object:
  `data/.cex002_harmonic_bundle/.objects/32/32029cf9cd182839719574f3963e2faa89935c682ed861712be5ef07c23a381c`,
  size 13,232,150 bytes, SHA `32029cf9cd182839719574f3963e2faa89935c682ed861712be5ef07c23a381c`.

Eleven manifests emitted under `.manifests/`, each hash-pinned in the descriptor (all eleven
`manifest_file_sha256` values matched the on-disk bytes):

| dataset_type | dataset_id | manifest bytes | manifest sha256 |
| --- | --- | ---: | --- |
| binance_usdm_perpetual_membership | ds_b452e9514e493a5fab256d79f15f73eeb7a2704fd46325199f3051b7cbd21a7c | 819034 | 2debc046929bc558a4c5f60393c6a21d7c4fa691d95cfba1c47845e0c600e6d4 |
| binance_usdm_bar_1h | ds_b2c4d1fdaee8a8e6ac520ef8959f6a0fa19d5cf127df322c8df8ff032d81f54f | 23429825 | 0509daef005c1e69628a4cbedf26ca8eb2ba2cb83cdd3486c87af004fb1d7b0a |
| binance_usdm_trade_flow_1h | ds_981249b1f68c7dd16de6767b5f0806a206769ffad77c2857b7a3d6b7fe89e938 | 24063824 | d57087de488e7c3277bfd0b7f4038610bf7edc859b8951851e047e1c1b80b2a8 |
| binance_usdm_open_interest_5m | ds_fcd0c228b6bc66df2f258e48bb2602d83d8c9a823ec2867e16d2a0591b0baa6c | 21288934 | c828699f30544876e7f3369708b298e6b21b62289adff68bfee3cca8e9e538e6 |
| binance_usdm_funding_realized | ds_bfb6848f0d29b471ad93276f5eb2ff130b8b40e5df86badc00a24ab93826c229 | 22581344 | 45aa5e721f131b89147044ada90c2a538388407d32edfa9c3c30cacdb019c34a |
| binance_usdm_funding_indicative_1h | ds_bdd0015c37254cd36c474f6a29f75d53a8039696c422cd265b6c78e4ee1cd287 | 27078785 | a6043d3aa14d5ca3997b981a1d3be36f97c376069cfcbfcb225450cfaae7898a |
| binance_usdm_mark_index_basis_1h | ds_3438d3af2b29c0d3bf1977f3c1a12c2ff981545f81c2ee0f562bd32c67a09a87 | 30630101 | 5336d0b72ccb04fda10a99823dbc668497cf49407947e35bf89e9704b3fd234e |
| binance_usdm_liquidation_observed_daily | ds_3d0dd49ae601b52f435e389366dc3c84e7f67c602d5c0d86ef04fdb41d4037dd | 21250406 | a1a66422e40f50a036463500cf59adcefaadae39269655ca3e782facdfc2511a |
| binance_usdm_cost_calibration | ds_8014c89843ac71148870b8834d1d88a2890fe87f62bf1049c68c42aa136e705a | 4637419 | 17932c0c0ba251e491529a3b54ec323597617dda2c2a80e1d9f5bb9545096e6b |
| binance_usdm_coverage_gap | ds_041104cd7efd60736c2bfebfd0233149a50640282a83802bbd687f041d254e72 | 52311439 | b385cdc64ab2c2001a494f9a3b5bb0f78c4318c0136a34541904ca2cba441ca6 |
| binance_usdm_harmonic_bundle | ds_07e037cd4e3a048b351d8cb6443c0720614356ac703e5283ba1ace88f66b5728 | 7404 | 0883526cfbe75cef6767eed1002133844c47fc0eb711366a45967a47ecf03fab |

Total manifest bytes: 228,098,515.

## Bundle footer / schema

- Bundle object: 13,232,150 bytes; Parquet rows 178,946; row groups 3.
- Schema: dictionary-encoded typed columns — `required_product`, `component`, `dataset_id`,
  `native_symbol`, `reference_identity_state`, `utc_month`, `unit_convention`,
  `censorship_semantics` (not null); `canonical_instrument_id`,
  `canonical_instrument_version_id`, `partition_sha256`, `partition_bytes`, `row_count`,
  `schema_sha256`, `lineage_manifest_sha256`, `lineage_mapping_count`,
  `source_report_sha256`, `source_manifest_detail_sha256`, `qualification_code_sha256`,
  `qualification_cli_sha256`, `sizing_code_sha256`, `sizing_cli_sha256`,
  `configuration_sha256`, `scenario_policy_sha256`, `coverage_gap_rows`,
  `typed_gap_membership_rows`, `fee_authority_gap_rows`,
  `cross_product_intersection_count`, `cross_product_intersection_sha256`.

## Counts, registries and dependencies

Eleven datasets, each with `quality_summary.schema_registry` version 1 (contracts per product
as listed) and `files[].partition.schema_ref`; metadata files carry rows 0. Total files
423,446 = 178,947 table + 244,499 metadata.

Bundle dependency edges: 10 (DATASET kind), roles: bar_1h, cost_calibration, coverage_gap,
funding_indicative_1h, funding_realized, liquidation_observed_daily, mark_index_basis_1h,
open_interest_5m, perpetual_membership, trade_flow_1h.

Liquidation `quality_summary`: `quality_gap_rows` 4,626; `authority_gap_rows` 202;
`comparison_entry_count` 18; `comparison_disposition` "pending_reviewer"; comparison SHA
`bd76dd2069e658ce11a00b7685e0008d4d5be0bec682acdf5640552a31af3391`.

Retained unreferenced kline inventory (separate audit):
- bar_1h: parquet_count 31, parquet_bytes 1,339,063, lineage_count 20,335, lineage_bytes 24,391,097.
- trade_flow_1h: parquet_count 47, parquet_bytes 3,553,501, lineage_count 20,335, lineage_bytes 24,675,787.

## Resources (measured)

- `_sqlite_reservation(manifests)` over the eleven emitted manifests: 3,458,088,960 bytes.
- Descriptor resources: `bundle_file_bytes` 13,232,150; `bundle_rows` 178,946;
  `metadata_remainder_bytes` 4,985,471,619; `release_metadata_pool_bytes` 5,556,368,003;
  `operating_reserve_bytes` 29,690,701,415; `operating_reserve_spent` false;
  `harmonic_bundle_allocation_bytes` 24,352,003; `unused_coverage_reservation_bytes` 114,144,134
  (non-reallocatable).
- Prepared descriptor bytes 11,020; preserved marker bytes 305; bundle object bytes 13,232,150.

## Catalog snapshot (read-only mode=ro, full ordered-row digests)

PRE-LAUNCH baseline:
- `cex002_reference_publication` rows: 0, ordered-row SHA-256 `4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945`.
- `cex002_bitmex_false_authority` rows: 5 (REJECTED/REGISTERED), ordered-row SHA-256
  `b4334b2c3f28d58a288b0130e1009dd305c5cf30b7e4af734f8036bd74d82103`.

POST-TERMINAL (success): identical digests — 0 rows and 5 rows respectively, same
ordered-row SHA-256 values. No catalog row was admitted. Free bytes after: 147,669,061,632.

## Scope limits and gaps

- The candidate is non-consumable; no catalog admission, proof, publication or consumer run
  occurred. No next ticket.
- The `_sqlite_reservation` value is the measured reservation for the eleven emitted
  manifests only; it is not a reauthentication of accepted tables.
- Record 509 is preserved unchanged; this record supersedes only the capacity-stop state.
- One bounded JSON-path inspector mistake during inspection (incorrect key paths) produced
  zero/None outputs; it was corrected with the reviewer-supplied exact paths and no data was
  affected. The corrected pass is the evidence above.

## Record status

Record 510 documents a successful non-consumable preparation with exact orphan disposal.
It claims no release or Gate acceptance. CEX-002 remains IN_PROGRESS; next ticket NONE;
reviewer acceptance remains exclusive.
