# CEX-002 Review 478 - Cost Calibration Source Authorization

- **Date:** 2026-09-08
- **Reviewer:** Lead Quantitative Finance Researcher/Engineer
- **Ticket:** CEX-002
- **Decision:** authorize Batch C source under the existing contracts
- **Gate 2:** `ACCEPTED`
- **Gate 3:** `IN_PROGRESS` - eight products accepted
- **Next required actor:** Sr Dev — Codex Sol
- **Next ticket:** `NONE`

## Assignment

The owner directs continued work and direct developer prompting. The reviewer assigns
GPT-5.6-sol High as the sole senior for Batch C, based on its accepted prior product work
and the authority, exact-numeric and publication risks here. Direct sub-agent delegation
and consolidated feedback are authorized for this drop. Existing role ownership remains.

Author exactly these three new paths:

- `src/cryptofactors/ingest/binance_usdm_cost_calibration.py`;
- `scripts/research/normalize_binance_usdm_cost_calibration.py`; and
- `tests/ingest/test_binance_usdm_cost_calibration.py`.

Deliver the complete source and test source, then stop for one consolidated reviewer
inspection. Do not execute tests, Ruff, acceptance commands, real normalization, integration,
Git, network, data mutation or repository-record edits. Hermes validation and integration
will be authorized with the source disposition. No other senior is assigned concurrently.

## Fixed input boundary

This is Review 474's existing Batch C, not a new acquisition plan or schema version.
ADR-0024/0025/0026/0027 and the accepted sizing contract govern. The five qualification
samples mentioned in ADR-0026 are not a cap on the complete frozen cost manifest.
The ticket and frozen `storage.cost_sample` require all 3,144 selected whole-day objects:
909 book-ticker and 2,235 book-depth objects, totaling 12,522,974,218 compressed bytes.
All source fields and rows must be retained. Do not substitute `cost_source_sample` or the
sizing coefficient cohort for this manifest. Do not acquire full historical book archives.

Read-only inspection of the accepted generation-0 completion table found 2,790 of these
keys present; the other 354 are book-ticker keys covered by the already accepted v3 direct
recovery (Review 415). Bind the disjoint union to the exact selected key set; no new
download or reopening of Gate 2 is required.

Pinned authorities:

- qualification report `research/sprint_004/62_CEX002_GATE1_SOURCE_PROCUREMENT.json`,
  SHA-256 `f27b2ba7e6eff3a8b1385d985c49ee64ef60a394737b1246130d0f37b9015f09`;
- sizing `research/sprint_004/258_CEX002_GATE2_STORAGE_SIZING_V3.json`,
  SHA-256 `3995a5072a7d84baecae677ceff6e1c7af9dd076daadec04a31717ffc8f16589`;
- complete cost manifest digest
  `04842ff6b9b58280b3ec2ea2644b3d44769be62d460bef785262cd4dd65cac57`;
- generation 0 `data/cex002_qualify/gate2/state.sqlite` and its `content/` sibling,
  seal head `8875338d0a2b7984fb8fefd7a716a04486667cfb1d726c3758f5496f065ef7ab`;
- v3 gzip JSONL manifest
  `data/cex002_qualify/gate2_revision_candidate_v3/manifest/4dacaba97c17ad9c4a9724f5db74dfab7ee98760cdb3df6dea46ab37c0684c2d.json.gz`
  (compressed SHA-256 is its filename), recovery root `data/cex002_recovery`;
- accepted membership completion
  `01d054b34c3a92cc349f9484296031e8cbb67ae7e62eb0a8b38c6d3928d977a3`
  (Review 465), exactly 771 native membership identities.

Reuse the existing generation-0 authentication and immutable-publication patterns without
editing accepted modules. Authenticate the report, sizing, sealed plan/completion/sidecar
chain, v3 manifest and selected raw bytes before their publication. Retained-credit states
remain valid only under the existing authenticated authority contract. V3 retrieval and
publication times not proved by retained evidence remain unknown. Preserve source key,
checksum, revision, raw ordinal, source event time and availability/retrieval distinctions.
No filesystem mtime becomes a historical availability clock.

## Product contract

Publish one hidden `binance_usdm_cost_calibration` product with the five heterogeneous
component schemas pinned in `typed_schema_contract.cost_component_schemas`:

1. `retained_book_ticker`: every selected update ID, bid/ask price and quantity,
   transaction time and event time, with raw reference/ordinal and native identity.
2. `retained_book_depth`: every selected timestamp, signed percentage band, depth and
   notional, with raw reference/ordinal and native identity.
3. `official_fee_schedule`: the schema-bearing zero-row component required by ADR-0026.
4. `fee_authority_gap`: exactly 771 instrument/version-scoped
   `historical_fee_schedule_unavailable` rows, using the accepted identity state and
   nullable canonical IDs honestly.
5. `scenario_policy`: exactly the two pinned ADR-0026 rows, 0.0005 primary and 0.0010
   sensitivity per executed side; `ASSUMED_CONSERVATIVE`, policy knowledge time
   `2026-08-23T03:00:00Z`, all credit/rebate/discount flags disabled, exact source basis.

These policy rows are immutable experiment configuration. They are not historical fee
observations, a historical upper bound, or backdated FEE-001 reference rows. Missing fees
never become zero cost. Zero rows are expected only for the explicit official-fee component.

Use frozen types, nullability, writer settings and component/native-symbol/UTC-month
partitioning. The unchanged cost allocation is 37,957,477,079 bytes, with 3,865 projected
component partitions (866 ticker, 2,226 depth, 771 fee gaps, one official-fee schema and one
scenario partition). Sizing row projections are bounds, not observed row counts. Keep
memory bounded by streamed row groups and one partition; do not materialize the entire
book corpus or all large partitions as Python rows. Use the existing 65,536-row writer cap.

Parse decimals and times exactly with integer/context-independent conversion. Preserve
headed/headerless formats, one-sided and empty quote states, and legitimate zero depth.
Do not impose positive liquidity or a two-sided-book requirement: ADR-0020 permits thin,
one-sided and empty quote states. Reject negative or inconsistent quote values, crossed
two-sided quotes, malformed fields, overflow, non-finite values and corrupt/unsafe ZIPs.
Repeated timestamps and depth bands are not a fixed-cadence missing-event grid. Retain
source observations and ordinals; do not silently deduplicate, repair or drop records.
Use transaction time for ticker partition attribution while preserving event time, and
source timestamp for depth; explicitly handle any source-day boundary observations
without silently omitting them. Report a source-contract conflict before inventing a rule.

Retain the frozen cost-sample source gaps with their native membership and family scope
in completion/lineage metadata for Batch D. Do not manufacture hourly/daily event gaps
between the selected sample days or expand coverage beyond the frozen sample.

Use content-addressed Parquet and lineage, no-clobber atomic publication, bounded staging,
schema/byte/row/hash verification, deterministic ordering and byte-identical replay. A
completion descriptor reconciles the exact source set, every component and physical row,
all schemas and code/config identities, partition/lineage digests, quote-state counts,
fee absence and policy meaning. Existing conflicting, symlinked, stale, unreferenced or
incompatible output must fail safely. No partial release is consumer-visible.

Test source must cover the real physical formats, exact numerics and clocks, quote/depth
states, full-manifest selection across generation 0 and recovery, authentication failures,
771-identity fee-gap/scenario semantics through bounded fixtures, partition streaming,
corrupt/unsafe input, no-clobber publication, interrupted replay and completion rejection.
Tests must not require production data or network and must not present fixtures as release
evidence. Report exact file hashes/line counts, design choices and any unresolved blocker.

## Review boundary and publication scope

Batch A/B remain accepted; do not rerun or alter them. Batch D, catalog transactions,
NautilusTrader, models and the next ticket remain unauthorized. Review 474's checklist is
unchanged. This source authorization is not product acceptance.

Under the reviewer governance-publication exception, the reviewer may stage, commit and
push exactly this review, `docs/handoff/CURRENT_TASK.md`, and `tickets/CEX-002.md`.
All unrelated dirty paths remain untouched. This publication executes no acceptance
commands, integrates no developer source and mutates no data.
