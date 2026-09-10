# CEX-002 Review 480 - Cost Acceptance and Coverage Source Authorization

- **Date:** 2026-09-09
- **Reviewer:** Lead Quantitative Finance Researcher/Engineer
- **Ticket:** CEX-002
- **Decision:** accept Batch C; reject the initial Batch D coverage source drop; authorize the consolidated correction below
- **Gate 2:** `ACCEPTED`
- **Gate 3:** `IN_PROGRESS` - nine of eleven products accepted
- **Next required actor:** Sr Dev - Codex Sol
- **Next ticket:** `NONE`

## Batch C acceptance

Accept finalizer integration `ab671b4713add0d9367c08cb18603f99b037fe1a`, Hermes
publication `d6d86e0900c051f938cdf91fb9ffeb6336baf766`, Record 479 and the completed
`binance_usdm_cost_calibration` product. HEAD and origin/main were both the publication
commit at review entry; the index was empty and the unrelated dirty baseline was preserved.
The original producer and all three finalizer file SHA-256 values still match Review 478.

Hermes reports 30 focused cases passing, clean Ruff/control/whitespace, one successful
finalization and its one authorized successful replay. Both runs returned completion
`fa4eced65e03e548cf5bf6500a9674a192a70dde9edf12d49c1f8bd539ad6f9e`; reuse changed from
false to true. The 455-second and 400-second durations in Record 479 are intervals between
observed pre/post-command timestamps, not instrumented process runtimes.

The reviewer independently hashed every file in the completed output and reconciled the
sole completion with every referenced Parquet and lineage, actual Arrow schemas, metadata
row counts, row-group limits, component totals, directory/file set and declared source
ordinal domains. All 7,731 preserved files also match Hermes's retained pre-run inode,
mtime and hash facts. The comparison checks the complete pre/post path sets, including
missing files, rather than only files that remain present.

| Fact | Verified result |
|---|---:|
| Completed tree files / directories | 7,732 / 11,387 |
| Preserved files / bytes | 7,731 / 17,940,823,719 |
| Completion bytes | 2,971,837 |
| Total logical output bytes / unchanged allocation | 17,943,795,556 / 37,957,477,079 |
| Partitions / matching lineages | 3,865 / 3,865 |
| Ticker / depth rows | 882,076,090 / 57,054,229 |
| Book rows / all component rows | 939,130,319 / 939,131,092 |
| Fee-gap / official historical fee / scenario rows | 771 / 0 / 2 |
| Source objects / compressed bytes | 3,144 / 12,522,974,218 |

Preserved inventory SHA-256:
`482cda93ba68c93d46a17207bbb6b01764dd5b66d72d936860eba67d2f399b98`.
Completed inventory SHA-256:
`90aaa5ae434dc1eaf9ef7aebc0d86c0af594fcf9edfb052d99a8ee80bbcab5f9`.
Both use Review 478's exact sorted path/sha256/bytes JSON encoding. The measured
source-row-facts digest remains
`aac31786a8f18088481cd00579c30dece80cf9907c792638d2e0047c076fc89b`.
Staging is empty, there is one completion, and no foreign or symlink artifact exists.

Reviewer helper `/tmp/cex002_review480_verify.py` completed with `result=PASS`. Its initial
attempt stopped after successful inventory hashing because it incorrectly expected
`utc_month` in fee-gap lineage; inspection confirmed the accepted component-specific
lineage shapes. Only the temporary reviewer helper was corrected. No producer, finalizer,
test, accepted artifact or implementation record was changed. No acceptance test or real
conversion was executed by the reviewer.

Acceptance retains Review 478's limits. Ticker rows exceed the old projection by
136,532,583; `ordinary_sizing_check_passed` remains false. The waiver applies only to
this exact reviewed inventory and does not alter Receipt 258 or the ordinary producer.
The quote-state counts remain 882,075,718 two-sided, 279 bid-only, 76 ask-only and 17 empty.
Fees remain unavailable historical authority plus two non-backdated assumed policies.
The prior complete raw-count/encoded-ordinal checks and bounded raw-value comparisons
remain the evidence for values; neither this review nor the finalizer claims independent
CSV-to-Parquet equality for every value. Batch C is complete; do not rerun it.

## Remaining fixed closeout

Review 474's original eleven products and Gates 0-5 remain the completion boundary. This
review authorizes coverage source only within Batch D, not a replacement batch, ticket,
schema, sizing receipt or acquisition plan. Bundle/catalog publication, clean NautilusTrader
readback, bounded one-minute/hourly comparisons, remaining independent economic examples,
and the full acceptance commands still require their subsequent bounded execution workflow.
Accepted Batch B reconciliation remains accepted with its measured OI differences and
unavailable overlaps; do not repeat it without an invalidating defect.

Two prerequisite observations are now explicit:

1. The holdout file `data/cex002_qualify/cex002_holdout_boundary.json` is present at SHA-256
   `2030e20aa5bd73df8fdbb7467e928508103b2e23659b85527101ec8b8546cb85`. Its boundary ID is
   `c842f813839e1dda375b351da0f693c54bcf932e33eb6e3394aba860c12346e2`, with UTC instant
   `2026-08-21T16:19:08.994166+00:00`, agreeing with the accepted qualification report.
2. Gate 0 is unfinished, not merely missing a citation. A read-only query of `exp003.db`
   on this review date finds all five exact BitMEX target IDs from Record 54 still
   `PASS / REGISTERED`, with row counts 14,376; 32,768; 32,768; 38,256; and 189,570.
   The rejected source findings in Review 59 remain unresolved authority. The unrelated
   root `control.db` contains no BitMEX dataset rows and is not evidence of quarantine.
   The SQLite query used `mode=ro` and `PRAGMA query_only=ON`; SQLite created untracked
   `exp003.db-shm` / `exp003.db-wal` coordination sidecars. These are left unstaged;
   no logical catalog row was changed and no cleanup was performed.
   This blocks final release acceptance, but does not invalidate the accepted Binance
   products or prevent independent coverage source work. No quarantine command or catalog
   mutation is authorized here. Its correction needs a separate exact-path assignment
   before final release, preserving the rejected dirty source until then.

## Sole senior source assignment

Select **GPT-5.6-sol, High reasoning**, as Sr Dev - Codex Sol, based on its accepted
price-state and cost implementations and familiarity with these exact authorities. No
other senior is concurrently assigned. The owner may relay this section as the complete
one-way prompt. Author exactly these three new files:

- `src/cryptofactors/ingest/binance_usdm_coverage.py`;
- `scripts/research/normalize_binance_usdm_coverage.py`;
- `tests/ingest/test_binance_usdm_coverage.py`.

On 2026-09-09 the owner explicitly authorized direct sub-agent launch for this assignment.
The reviewer launched Sol High, may receive its complete drop and deliver consolidated
source feedback directly, and retains the source-only boundary below. This replaces
manual relay for this drop; Hermes's integration and validation ownership is unchanged.

The reviewer checked the five accepted 0GUSDT September 2025 timestamp columns read-only,
authenticating the selected partition hashes. Bar/OI/funding/basis/liquidation rows are
321 / 3,843 / 233 / 206 / 14. The five-product observed-day intersection is September
22-30 (nine days); complete hourly/OI/basis cadence with observed funding and liquidation
presence is September 23-30 (eight days). September 22 has only 14 basis rows. Funding
counts change during the month and do not establish an expected settlement schedule.
This bounded source-review check is not a coverage run or an accepted coverage product.

Do not edit existing source, exports, tests, ADRs, records, configuration or data. Author
the complete coverage/gap producer and its full daily alignment report together. The
senior returns the complete drop with file SHA-256 values and line counts for one
consolidated reviewer inspection. No test execution, Ruff, real run, network, Git,
integration, record publication, catalog, quarantine or other-product mutation is assigned.
Hermes remains unauthorized until source acceptance supplies its complete workflow.

### Inputs and authority

Use the accepted report and Receipt 258 with hashes
`f27b2ba7e6eff3a8b1385d985c49ee64ef60a394737b1246130d0f37b9015f09` and
`3995a5072a7d84baecae677ceff6e1c7af9dd076daadec04a31717ffc8f16589` respectively. Pin the
holdout above and all nine product completions below. Paths are repository-relative;
price-state partition paths resolve against `data/.cex002_price_state`, as their existing
descriptors specify, not against the nested completion parent.

| Product root under `data/` | Sole completion SHA-256 |
|---|---|
| `.cex002_perpetual_membership` | `01d054b34c3a92cc349f9484296031e8cbb67ae7e62eb0a8b38c6d3928d977a3` |
| `.cex002_bar_1h` | `3b803d3e84e5d0bf87064626cc0504e9ff92e225a53ba83cdd4e09c38a2e9fd7` |
| `.cex002_trade_flow_1h` | `a165f9e57065514cadc95620c280a82dbad5032d17c19e1caf012c9d12a84d0a` |
| `.cex002_open_interest_5m` | `bb089fc992326c66ddb65cea03dda92e8cd9fcf7cb7f373821f04a16db9168e4` |
| `.cex002_funding_realized` | `57628164f19d182164b6058d9e51f794430cc918706c088f430e1c01d2898522` |
| `.cex002_price_state/binance_usdm_funding_indicative_1h` | `360eb662ab89c47ca1f6db754b74f486a42de4aa116970221f0739268a51fba0` |
| `.cex002_price_state/binance_usdm_mark_index_basis_1h` | `b698c0543c281e3244e0c3358ea7ce1f347bc591b06a076058fed749d05584f0` |
| `.cex002_liquidation_observed_daily` | `dc4127dccad31477cb72ec6fdf076dbdbdef34a1212d4f090d5f421b96dc267f` |
| `.cex002_cost_calibration` | `fa4eced65e03e548cf5bf6500a9674a192a70dde9edf12d49c1f8bd539ad6f9e` |

Accept only safe regular contained artifacts and their actual pinned schemas. Bind every
consumed coverage input to its descriptor, hash and lineage; a directory listing alone is
not authority. Do not re-download, re-normalize, reopen accepted economic decisions, or
repeat complete raw-value audits. Cost is bounded calibration evidence: use its accepted
completion/source-gap/lineage facts without rescanning 939 million book values. Report
source-day precision honestly where exact cost event extrema are not in those facts.
Preserve native identity and the accepted explicit canonical-null state.

### Coverage and gap contract

1. Preserve all 771 accepted identities, including 73 funding-only identities; report
   the 237 excluded classifications separately. Product absence never removes membership.
   Derive the full historical reporting domain from the accepted report's source and
   membership bounds and actual product ranges, never today's date, a current-listing
   filter, or the liquidation overlap alone. Retain explicit before/after-family and
   unknown-onboard/close distinctions; observed endpoints are not asserted listing dates.
2. Publish the frozen 23-column `binance_usdm_coverage_gap` source-gap representation
   and the existing typed-gap-membership and quality-gap component schemas from Receipt
   258. Preserve all 8,317 source-gap records and 3,742 typed-gap memberships exactly.
   Reference the 771 accepted cost fee-gap rows without manufacturing another fee history.
   Keep original qualification gaps distinguishable from normalized observed quality
   gaps and recovery dispositions; an old source gap is not automatically a current
   missing observation. Preserve the HBARUSDC checksum conflict, product-specific kline
   exclusions, price-state unjoinable ranges, liquidation gaps and 494 cost source gaps.
3. Reconcile each accepted product's physical, retained, duplicate, excluded and
   unjoinable row equations using its existing definitions. Do not add component counts
   with different meanings or count a shared source multiple times as independent input.
   Bind existing gap artifacts rather than altering them. For fixed cadence, calculate
   expected/observed/missing counts from the actual accepted time domain; OI retains its
   native five-minute phase and midnight-spillover disposition. Funding remains observed
   events with source-declared intervals; no eight-hour grid, invented settlement,
   forward fill or zero substitution is permitted.
4. Produce a content-addressed coverage report as part of the same product completion,
   with per-instrument/product first/last observed times, time precision, counts and
   their units, expected-count basis (null where not established), gaps, duplicates,
   source revisions and input descriptor identities. Include identities with no rows.
   A projected count from sizing must never be reported as an observed count.
5. Include the complete UTC-day alignment over the declared historical reporting domain
   in deterministic, bounded symbol/month report partitions. Keep the native products
   separate. Each date reports price, OI, realized funding, basis and observed liquidation
   presence, observed counts, fixed-cadence completeness where established, and explicit
   exclusion reasons. Distinguish the five-product observed-day intersection (all five
   have actual observations) from full-cadence coverage. A single hourly row is presence,
   not a complete day. Funding absence is no observed settlement with unknown expected
   count, not zero funding; liquidation presence never becomes uncensored completeness.
   Do not turn unknown source availability into a causally usable vintage. Publish
   counts/digests for the aligned day set and both stated coverage predicates so the
   later bundle cannot confuse the projected symbol/month intersection with actual days.
6. This is coverage accounting, not daily feature construction. Do not resample stock OI
   by summing it, convert premium into indicative rates, synthesize daily funding,
   reclassify fee scenarios, infer missing zeros, or invent daily OHLCV observations.
   Retain source-availability and retrieval semantics in the referenced lineage.

### Publication, bounds and test source

Use ADR-0024's existing partition-atomic, content-addressed, no-clobber, fsync and
completion-last pattern in a caller-selected hidden output root. Never mutate any input
tree. Replay must authenticate dependencies and reuse byte-identical output; conflicting,
stale, unsafe, foreign or incomplete input fails closed. Coverage completion is not a
visible harmonic bundle or a catalog transaction.

Use the existing writer and frozen component allocations from Receipt 258. Source gaps
are bounded at 8,317 rows / 4,817 partitions / 36,831,146 Parquet bytes; typed memberships
at 3,742 rows / 3,742 partitions / 7,757,166 bytes. The quality-gap reservation is a
ceiling of 216,934,972 rows / 130,820 partitions / 9,154,761,060 bytes, never a production
target. Enforce the receipt's largest-file and total byte bounds too. Coverage report,
lineage and completion bytes must be explicitly measured and charged within the existing
applicable coverage/metadata allocation, with no double allocation or changed sizing
coefficients. Keep at most one symbol/month's observations in memory; incremental counts
and descriptor indexes may persist. Do not materialize whole-history market rows or the
full universe/day matrix in memory. Expose explicit authority/input/output path arguments
and return a concise JSON result. No real output root is created by the senior.

**Exact metadata sub-budget clarification:** daily alignment is symbol/month JSON report
metadata, not an additional Parquet schema or required product. Compact shared field and
product names with per-day records are permitted; loss of dates, counts or semantics is
not. Receipt 258 reserves 4,817 source-gap, 3,742 typed-gap and 130,820 quality-gap catalog
pages, at 4,096 bytes each. Their existing 139,379-page reservation supplies a single
**570,896,384-byte coverage metadata sub-budget** for all daily reports, instrument/product
summaries, lineages, completion and any copied metadata together. Each gap Parquet component
retains its separate unchanged ceiling. Bytes may be counted in only one category.

This is a subdivision of the unchanged 5,556,368,003-byte release-wide
`capacity.catalog_manifest_bundle_bytes`, not a new allowance. Reserve/debit 570,896,384
once for coverage metadata, leaving **4,985,471,619 bytes** reserved for the remaining
release metadata/catalog work. Coverage completion must declare the source page counts,
page size, reserved debit, measured category bytes and remainder. The later bundle must
honor this ledger; it may not allocate the whole release allowance a second time. Unused
coverage reservation is not implicitly available to another component. A metadata overrun
fails without trimming coverage, changing coefficients or claiming a sizing pass. This
clarification resolves the senior's allocation question before implementation; existing
publication architecture, schemas and aggregate capacity remain unchanged.

Author meaningful fixtures covering the frozen schemas; all membership classes; source
versus observed gap distinctions; unknown bounds; native-phase OI and midnight boundaries;
variable-interval funding; zero observed liquidations versus missing rows; partial days;
unmatched price-state coverage; unknown availability; row-equation reconciliation;
path/descriptor/schema/hash refusal; memory bounds; byte limits including metadata;
interrupted completion-last publication; concurrent no-clobber; and byte-identical replay.
Tests must demonstrate that a common symbol/month is insufficient to prove common days.
Return source for review and stop. The initial assignment granted no targeted test exception;
the corrective assignment below grants one exact command.

## Initial coverage source review and consolidated correction

The reviewer rejects the complete initial source drop for integration. This is a static
source decision, not an executed test result or a rejection of any accepted input product.
The three inspected files have these identities:

| Path | Lines | SHA-256 |
|---|---:|---|
| `src/cryptofactors/ingest/binance_usdm_coverage.py` | 1,285 | `8ff893b28c8b9f185f9ca72e13297c2dede266f0a5556cabbad3175a295fa3cd` |
| `scripts/research/normalize_binance_usdm_coverage.py` | 85 | `567f8ce77b7f19d1174fd9a9c074d541ac7cab823c63957a32f739c8b1097f5f` |
| `tests/ingest/test_binance_usdm_coverage.py` | 560 | `2acb4fe3126e433f84166b3298f39e7dec563e1af6e42eff037d274d7ea7d4bb` |

The same Sol High actor is authorized to correct the production and test files above.
The CLI has no identified blocker and remains unchanged. Return one complete corrective
drop covering this entire list; no intermediate integration or real run is authorized.
The original input pins, schemas, source/metadata allocations, membership domain, and
financial semantics remain binding.

1. **Accepted OI schema and native timestamps (blocking).** `TIMESTAMP_COLUMNS` selects
   `calc_time`, but the accepted product field is `create_time`. `_scan_partition`
   (initial lines 542-567) also requires absolute five-minute clock alignment, and
   `publish_quality_gaps` (lines 862-866) repeats that requirement for gap endpoints.
   These contradict accepted Reviews 436/437/445: retain exact source milliseconds,
   native offset phases, prior-observation-phase missing runs, and the accepted midnight
   exclusion disposition. Use the actual frozen schema. Preserve valid irregular
   intervals without asserting that they establish complete cadence. Cover nonzero
   phase, 301-599-second intervals without invented missing rows, off-phase missing runs,
   and UTC-month boundaries with independently specified fixtures.
2. **Publication and completion proof (blocking).** `_OutputTree.publish` (lines 621-655)
   closes the staged file before its hook/rename and never verifies newly published
   bytes. Replacing or modifying that staged file can publish incorrect bytes under the
   original digest. `audit` checks names/set membership only. `normalize_coverage`
   publishes completion before its sole audit (lines 1266-1268), so a pre-existing foreign
   digest-shaped artifact can cause failure only after a completion is visible. Hold
   safe directory/file descriptors through publication, verify staged and winning bytes,
   Parquet schema/rows and declared sizes, and reprove the complete expected inventory
   before exposing completion. Verify replay dependencies and output contents, not just
   filenames. Refuse stale/foreign files, unexpected directories and non-regular entries.
   Preserve no-clobber concurrency, bounded staging, fsync and safe reuse after interruption;
   clean only positively owned temporary files on handled failures. Do not delete foreign
   leftovers or mutate accepted inputs. Tests must inject staged and destination mutation,
   a foreign digest-shaped artifact, and interruption before completion.
3. **Input containment and scan identity (blocking).** `_require_safe_path`, `_file_sha`
   and the later `pq.ParquetFile(path)` independently reopen pathnames. Parent replacement
   or input mutation between authentication and scan can detach the reported descriptors
   from consumed bytes. Use descriptor-relative no-follow traversal and bind scans to the
   authenticated regular file; reprove consumed dependencies before completion. Detect
   source/parent substitution using bounded fixtures. `_safe_relative` also normalizes
   `./local` before inspecting its parts, contradicting the explicit refusal test;
   validate the original path spelling and unsafe components before normalization.
4. **Daily cadence and exclusion reasons.** `publish_reports` (lines 1007-1011) equates
   24/288 row counts with complete cadence. `_scan_partition` counts duplicates while
   separately recording them, so duplicated timestamps can conceal a missing slot. Prove
   distinct observed slots and the applicable native cadence; preserve actual observation
   counts and valid OI phase changes without rounding or inventing observations. A partial
   observed day currently has `complete=false` but no exclusion reason. Report explicit
   reasons for failure of each applicable full-cadence predicate as well as absence,
   retaining unknown event expectations and censored liquidation semantics. Keep the
   0GUSDT nine-day presence/eight-day cadence reference case above.
5. **Cost summary facts.** `publish_reports` (lines 1076-1088) labels per-instrument counts
   unavailable although its pinned partition descriptors already provide known component
   row counts. Report those counts separately with their actual units; do not combine
   book observations, fee gaps and scenarios as one economic count. Authenticate the
   referenced cost lineages needed for source-day extrema and report those actual dates
   at day precision. Exact event-time extrema and unestablished duplicate statistics may
   remain null. A `source_day_only` label without source days does not satisfy the report
   contract. Do not rescan book-value Parquet rows.
6. **Test contracts and complete producer coverage.** The test file uses `Mapping` at
   line 423 without importing it. Line 109 expects `canonical_reference_unavailable`,
   whereas the accepted sizing/native-identity contract is
   `reference_identity_not_yet_created`. The liquidation test at lines 258-270 removes
   the whole partition but expects the different reason used for an absent day within an
   existing partition. Correct the contracts, and distinguish a real zero-valued observed
   liquidation row from a missing row. Current fixtures derive timestamp columns from
   the implementation and reproduce `calc_time`; they cannot detect the real schema
   mismatch. Add a bounded fixture with actual authority/completion/lineage/schema shapes
   that exercises `load_inputs` and the complete `normalize_coverage` path through
   completion and byte-identical replay. Test all membership classes, rowless identities,
   source-versus-observed gaps, component and metadata bounds, and the failure paths
   above. Fixture-only pins/bounds may be controlled inside tests; production pins and CLI
   authority must remain strict. Do not claim helper-only publication as producer replay.

The reviewer executed no source tests, Ruff, conversion, integration, or data mutation.
The deterministic assertion mismatches above were identified by reading the source and
accepted contracts; they are not claimed as observed pytest output.

After completing all edits, Sol may execute exactly once under the AGENTS.md targeted
senior test exception:

```bash
PYTHONPATH=src .venv/bin/python -m pytest tests/ingest/test_binance_usdm_coverage.py -q --tb=short
```

This single focused command is for immediate corrective source feedback. Stop on its
first nonzero result and report the exact command and complete output; do not patch and
retry, run Ruff, expand tests, or execute real data. Even a passing result does not accept
or integrate the drop. Return all three file hashes/line counts, the bounded change
description, and the command result. Hermes retains all integration, acceptance, evidence,
record and implementation Git ownership. The reviewer may deliver this correction to
the existing directly authorized Sol sub-agent and will not poll for progress.

## Reviewer publication scope

Under the AGENTS.md reviewer governance-publication exception, publish exactly:

- `research/sprint_004/480_CEX002_COST_ACCEPTANCE_AND_COVERAGE_SOURCE_AUTHORIZATION.md`;
- `research/sprint_004/478_CEX002_COST_CALIBRATION_SOURCE_AUTHORIZATION.md` (supersession notice only);
- `tickets/CEX-002.md` (current checklist/action only);
- `docs/handoff/CURRENT_TASK.md`.

Repository-control and whitespace validation here govern this documentation publication;
no full-ticket acceptance command results are claimed. No developer source, test,
implementation record, raw/normalized data or catalog state is integrated or changed.
