# CEX-002 Review 483 - Coverage reconciliation recovery

- **Date:** 2026-10-16
- **Reviewer:** Lead Quantitative Finance Researcher/Engineer
- **Ticket:** CEX-002
- **Decision:** accept Record 482 as a terminal failure disclosure; authorize bounded audit-helper preparation only
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
