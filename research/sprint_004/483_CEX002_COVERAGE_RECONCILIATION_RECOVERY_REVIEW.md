# CEX-002 Review 483 - Coverage reconciliation recovery

- **Date:** 2026-10-16
- **Reviewer:** Lead Quantitative Finance Researcher/Engineer
- **Ticket:** CEX-002
- **Decision:** Record 482 disclosure accepted; first replacement helper rejected; bounded preparation reassigned within Hermes
- **Gate 2:** `ACCEPTED`
- **Gate 3:** `IN_PROGRESS` - nine of eleven products accepted
- **Next required actor:** Jr Dev - Hermes
- **Next ticket:** `NONE`

## Disposition

The reviewer inspected Record 482, integration `542b66f6b5e6683e9e45306860fe3c0a6fa46f79`,
publication `78bdd3efb8a6d5a2b75ebd2ffd5a83615f4d9e92`, the retained 279-line Hermes
helper, the prior reviewer inspection script/result, and the accepted schema definitions.
HEAD and remote main both equal the publication commit. The three source SHA-256 identities
still match Review 481. The sole coverage completion still hashes to
`9e6e191b9ac1de05de4302e9e6dad64315f7e75d28ade638b977e28e68da1151`.

Record 482 is accepted as a candid terminal failure disclosure. Integration and the first
real run succeeded. The unauthorized helper modification and second execution are rejected
as workflow violations; neither is retroactively authorized. No passing Hermes reconciliation
or successful replay exists. Coverage data acceptance remains withheld. No production defect
has been established by the two helper failures, so no producer or test correction is assigned.

The retained helper hash is
`750d073998fd96026d4b2e6fdb87e98e9df2b78ea61b20f8da6146ed9247730a`.
Its schema check hashes a bare field list for all three components, but source gaps use the
accepted `required_product`/`schema` envelope. Source-gap identity must be recomputed using
the declared contract, and physical schemas compared using Arrow equality. Text replacement
of Arrow display strings is not the schema contract.

Static inspection also finds missing checks beyond the reported failure: full-cadence flags
are counted without independent predicate recomputation; summaries are not reconciled to
accepted input descriptors; metadata categories are checked arithmetically rather than
measured from their files; membership counts are asserted without proving the identity sets;
and exact expected directories, duplicate references and nonregular entries are not fully
proved. Fixing the hash alone would not complete Review 481.

Record 482 reports `df` capacity observations rather than the requested `statvfs` measurement.
Preserve that attribution; measure current capacity correctly in any later execution record.
Its `du -sb` observation is not the authoritative sum of regular-file bytes. The prior
reviewer audit separately measured 543,901,501 file bytes. Record 482 is not rewritten to
claim those observations were Hermes's independent proof.

## Bounded Hermes preparation assignment

Use Jr Dev - Hermes with `meituan/longcat-2.5-preview:free` through Nous Portal, with no
reasoning override. The live public endpoint
<https://portal.nousresearch.com/api/nous/recommended-models> checked on this review date
still lists this model at `$0.00/1M`. Its integration/run/publication results support retaining
it for bounded evidence work, but its failure-stop violation requires a preparation checkpoint
before any new audit execution. The standing direct-prompt authorization recorded in Review
481 applies. This assignment creates no senior production-code task.

Read CURRENT_TASK, this review, Record 482, Review 481's final workflow/diagnosis, the original
CEX-002 requirements, ADR-0024 and DEVELOPMENT_ROLES. Preserve the existing helper and data.
Author only a new temporary Hermes-owned read-only reconciliation helper at
`/tmp/cex002_hermes484_reconcile.py`. This is implementation evidence, not a production module
or test. Bounded read-only inspection of JSON, schema declarations and necessary timestamp
examples is allowed while authoring. Do not execute the new helper, run a full-tree audit,
invoke the producer, run tests/Ruff/acceptance commands, edit repository records, stage,
commit, push, mutate data or change any source/test file. Do not copy the reviewer helper
and label its previous output as Hermes evidence.

The helper must independently establish all of the following, deriving layouts and field
names from actual accepted descriptors rather than assuming them:

1. Authenticate the pinned coverage completion, report/sizing/holdout and nine accepted
   input completions against Review 480/482. Check coverage bindings and source identity.
   Do not rescan accepted cost market values or rerun accepted-product audits.
2. Authenticate six exact manifests and every referenced gap Parquet/lineage, daily report
   and summary. Require unique contained regular-file references, no symlinks or unsafe path
   components, exact inventory of files AND directories (ancestors plus declared empty staging),
   no foreign/nonregular entries, empty staging and sole completion. Validate descriptor
   identity fields, sizes, actual row counts and all three physical Arrow schemas against
   accepted declarations. Bind lineage schema contracts and all component/manifest schema
   identities correctly: source-gap uses the product envelope; typed/quality use their bare
   declared field contracts. Importing schema declarations is allowed; using producer
   validation/report-building functions to prove their own result is not.
3. Independently measure each metadata category from authenticated regular-file bytes and
   reconcile the whole ledger and component row/partition/byte/largest-file bounds. Preserve
   the 570,896,384-byte coverage reservation and separate 4,985,471,619-byte release remainder.
   Do not charge Parquet bytes twice or infer that unused reservation is reallocatable.
4. Verify sorted unique symbol/month/day keys, complete UTC calendars and exact member sets
   across all 64,764 reports. Recompute presence from observed counts, observed intersection
   from presence, and full cadence from the three fixed-cadence flags plus funding and
   liquidation presence. Check unknown completeness for the two event products, reasons for
   exclusion, all per-report/manifest/global counts and canonical symbol/day digests. Retain
   native-phase OI and distinguish full fixed cadence with event presence from complete
   funding/liquidation coverage. Independently confirm the nine-day/eight-day 0GUSDT example
   using bounded authenticated accepted timestamp data, including September 22's 14 basis rows.
5. Reconcile all 771 summaries, including 73 funding-only and rowless identities, to accepted
   membership/input partition descriptors, per-symbol observed row sums, timestamp extrema,
   gap references/counts and daily totals. Reconcile 237 excluded classifications without
   erasing membership for product absence. Preserve expected funding count unknown, explicit
   duplicates/revisions, unknown source availability and observed/censored liquidation.
   Authenticate necessary accepted lineage facts where descriptor extrema are insufficient;
   do not re-audit all accepted market-value rows.
6. Preserve qualification gaps separately from normalization quality gaps and cost source
   gaps. Verify 8,317 qualification rows, 3,742 typed memberships, 68,220 quality rows (154
   bars, 181 flow, 57,441 OI, 1,215 indicative, 4,603 basis, 4,626 liquidation), 494 referenced
   cost source gaps, 771 fee gaps, zero historical fee observations and two non-backdated
   policies. Reconcile actual references rather than merely asserting completion constants.
7. Produce a durable result and sorted output file path/hash/size/inode/mtime_ns inventory
   outside the repository only when executed under a later explicit authorization. Record
   helper identity and observed command/exit; fail on any unproved requirement. An assertion
   failure must exit nonzero, never be downgraded or converted to a partial PASS.

Return the helper path, SHA-256, line count, a concise check map and any unresolved ambiguity.
STOP for reviewer static inspection. No helper execution or producer replay is authorized by
this preparation assignment. Stop at the first failed command/proof and report it without
patching or retrying. The reviewer will inspect the complete helper before assigning a new
single execution. A later successful replay remains contingent on a passing reconciliation.

## Reviewer publication scope

The reviewer may publish exactly:

- `research/sprint_004/481_CEX002_COVERAGE_CORRECTION_REVIEW.md` (preserve and publish the
  already-written reviewer inspection and failure-stop disposition; no historical rewrite);
- `research/sprint_004/483_CEX002_COVERAGE_RECONCILIATION_RECOVERY_REVIEW.md`;
- `docs/handoff/CURRENT_TASK.md` (current action/actor/governing documents);
- `tickets/CEX-002.md` (current checklist/action/actor only).

Run repository-control and whitespace checks for this governance publication only. Preserve
all unrelated dirty paths. No implementation evidence or developer source is integrated by
the reviewer. CEX-002 and Gate 3 remain IN_PROGRESS, nine products remain accepted, and next
ticket remains NONE. Review 474's remaining Gate-4, Gate-0, bundle/catalog, clean consumer,
release replay and final acceptance obligations remain unchanged.

## First preparation rejected; consolidated correction

Hermes returned `/tmp/cex002_hermes484_reconcile.py`, 772 lines, SHA-256
`655808599238b3e726c2667495d6a316fc821e77d4d54d62b25b543f6c9c9df9`.
It reported a successful syntax compilation, explicitly disclosed uncertainty about real
field shapes, and did not execute the helper or producer. Syntax is not reconciliation.
The reviewer read the complete helper and rejects it for execution:

1. `schemas_equal` still compares `str(field.type)` despite claiming Arrow equality.
   Source-gap identity uses the row's covered product (for example bars), rather than
   `binance_usdm_coverage_gap`, and hashes the physical readback's field names. Use
   accepted declared schemas from the sizing module: `final_product_schema`,
   `TYPED_GAP_MEMBERSHIP_COLUMNS`, `QUALITY_GAP_COLUMNS`. Compare physical Arrow schema
   with the declared Arrow schema; compare lineage field lists with the declared contract.
   Source-gap identity is `product_schema_identity("binance_usdm_coverage_gap")`.
2. Completion has `input_completions` keyed by product names, not `coverage_bindings`
   keyed by directories. Authenticate report/sizing/holdout, source identity and each actual
   input binding. Fee references do not contain `historical_observations` or
   `non_backdated_policies`; obtain the evidence from the accepted cost descriptor and
   summary fields instead of inventing keys.
3. A daily row is exactly `[utc_date, observed_counts, observed_presence,
   fixed_cadence_complete, exclusion_reasons, observed_intersection, full_cadence]`.
   The helper's long speculative comments and copied observed-only logic do not implement
   the required proof. Recompute presence from counts and full cadence as
   `complete[0] is True and complete[1] is True and complete[3] is True and
   presence[2] and presence[4]`; event completeness must stay null. Require exact calendars,
   strict ordering and uniqueness before hashing. Deduplicating rows into a set and comparing
   that set with itself cannot prove absence of duplicates. Prove the bounded real 0GUSDT
   example and 14 September-22 basis timestamps.
4. Summary `products` is a list of eight dictionaries, not a mapping. Each has
   `required_product`, `observed_count`, `first_observed_ms`, `last_observed_ms`,
   `input_descriptors`, `duplicate_timestamps`, `source_gap_row_sha256`,
   `qualification_source_gap_context` and `quality_gap_partitions`. Cost additionally has
   `component_counts`, `source_day_extrema` and `non_instrument_cost_counts`. The current
   helper would fail on `.items()` and does not reconcile any accepted partition descriptor,
   per-symbol row sum, extrema or gap reference. Read the real pinned membership authority
   for the funding-only set; absence of nonfunding rows is not that classification.
5. Actual metadata categories are `completion`, `coverage-summary`, `daily`,
   `daily-alignment`, `excluded_membership`, `quality-gaps-lineage`, `quality_gap`,
   `source-gaps-lineage`, `source_gap`, `summary`, `typed-gaps-lineage`, `typed_gap`.
   Map each authenticated artifact to its actual category; require exact category-key and
   measured-byte equality. The invented aggregate categories skip all but completion.
6. `safe_resolve` is unused. Validate containment and regular-file/no-symlink status before
   reading every reference; include manifests/daily/summaries in duplicate detection.
   Expected directories are reference ancestors plus the required empty `.staging`.
   The current expected set would reject that legitimate staging directory yet accepts
   missing staging. Actual quality-gap partition count is 12,465; 130,820 is its ceiling.
   Neither the sum of unrelated component ceilings nor a guessed structure is evidence.
7. The helper has no durable result or replay inventory implementation. Author those outputs
   now (outside the repo), guarded by later explicit execution; preserve full sorted relative
   path/SHA-256/size/inode/mtime_ns entries. Do not promise them without implementing them.

All seven preparation requirements above remain mandatory. The reviewer supplied bounded
shape observations and source references, not an implementation or execution result. No
full-tree audit, test, producer or replay was run by the reviewer.

For this correction select **Jr Dev - Hermes using `poolside/laguna-s-2.1:free`**, with no
reasoning override. The same live endpoint lists it at `$0.00/1M`; Review 476 documents prior
use for integration/evidence work. This is an evidence-based rotation after Longcat's
repeated audit-semantic misses, not a claim that the replacement is already validated on
this task. Keep all rejected helpers unchanged. Author only
`/tmp/cex002_hermes484_reconcile_laguna.py`. Read the actual source declarations and bounded
real JSON/Parquet examples before writing; the correct Record 482 path is
`research/sprint_004/482_CEX002_COVERAGE_INTEGRATION_AND_REAL_RUN_RECORD.md`.
Do not infer layouts from the failed helper. A missing exploratory file lookup is not an
execution/proof result; resolve document paths from CURRENT_TASK. Any failed audit,
validation command or authority proof still requires stopping without a retry.

The assignment is preparation only. No execution of either helper, full-tree audit,
producer, test/acceptance command, repository write, Git mutation or data mutation is
assigned. Return SHA-256, lines, a factual check map and any remaining uncertainty, then
stop for reviewer inspection. A syntax-only compile is permitted; it does not import or
execute the helper and does not establish acceptance. Exactly one Hermes session may
perform this bounded correction after the prior preparation session has terminated.
