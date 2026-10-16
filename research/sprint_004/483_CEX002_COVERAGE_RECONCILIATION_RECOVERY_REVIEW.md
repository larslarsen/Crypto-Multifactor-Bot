# CEX-002 Review 483 - Coverage reconciliation recovery

- **Date:** 2026-10-16
- **Reviewer:** Lead Quantitative Finance Researcher/Engineer
- **Ticket:** CEX-002
- **Decision:** checker integrated and real reconciliation PASS; replay and follow-up inspection blocked by approval gate; Hermes stopped
- **Gate 2:** `ACCEPTED`
- **Gate 3:** `IN_PROGRESS` - nine of eleven products accepted
- **Next required actor:** Lead Quantitative Finance Researcher/Engineer
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

## Preparation discovery stop and exact-path continuation

The Longcat session `20261016_142047_361cc5` returned the rejected helper, then continued
with an additional static check. The reviewer interrupted it; terminal exit was 130.
The helper still has its rejected hash above. No helper execution or producer run occurred.

Laguna session `20261016_143823_76bfa2` did not create its assigned helper. Its exploratory
command below returned exit 1 because some temporary directories were inaccessible:

```bash
find /home/lars/Crypto_Multifactor_Bot/research -name "*482*" -o -name "*481*" -o -name "*483*" 2>/dev/null; echo "---"; find /tmp -name "*cex002*" -o -name "*hermes484*" 2>/dev/null
```

A separate already-issued `find /home/lars/Crypto_Multifactor_Bot -name "*.py" | head -60`
returned exit 0 and listed virtual-environment files. The reviewer interrupted the session
at this discovery failure; terminal exit 130. This is a tooling/discovery stop before any
helper creation, audit, replay or data mutation, not a product failure. The reviewer inspected
the redacted session export read-only to establish the exact command and exit.

The reviewer now authorizes one continuation of the same Laguna preparation assignment.
No audit retry is involved. Avoid broad directory discovery; all needed paths are known.
Use direct reads of these existing files and bounded artifact paths derived from the pinned
coverage completion/manifests:

- `/home/lars/Crypto_Multifactor_Bot/src/cryptofactors/ingest/binance_usdm_coverage.py`;
- `/home/lars/Crypto_Multifactor_Bot/src/cryptofactors/acquisition/binance_usdm_harmonic_sizing.py`;
- `/home/lars/Crypto_Multifactor_Bot/research/sprint_004/482_CEX002_COVERAGE_INTEGRATION_AND_REAL_RUN_RECORD.md`;
- `/home/lars/Crypto_Multifactor_Bot/docs/engineering/DEVELOPMENT_ROLES.md`;
- `/tmp/cex002_hermes484_reconcile.py` (rejected, read-only);
- `/home/lars/Crypto_Multifactor_Bot/data/.cex002_coverage/.complete/9e6e191b9ac1de05de4302e9e6dad64315f7e75d28ade638b977e28e68da1151.json`.

Use `rg` only on the named source paths if locating definitions. Do not walk `/tmp`, the
virtual environment, unrelated repositories or the prohibited archive. Preserve the same
preparation-only write path, seven requirements, consolidated corrections and static-review
stop boundary. The first nonzero execution/proof still stops this continuation. No audit,
replay, producer or repository mutation is authorized.

## Continuation terminal disposition - internal approval denial

The resumed Laguna session read the named source files and pinned completion successfully
through read-file tools. Its later proposed terminal command to inspect completion JSON
was denied by Hermes's internal approval gate after a timeout. Observed UI:
`Timeout — denying command`. Tool result: `exit_code: -1`, `status: blocked`, empty output,
and the explicit instruction not to retry, rephrase or pursue the same result through a
different command. The exact proposed command text retained in the session is:

```text
cd /home/lars/Crypto_Multifactor_Bot && PYTHONPATH=src .venv/bin/python -c "
import json
with open('data/.cex002_coverage/.complete/9e6e191b9ac1de05de4302e9e6dad64315f7e75d28ade638b977e28e68da1151.json') as f:
    c = json.load(f)
print('TOP KEYS:', sorted(c.keys()))
print()
print('manifests keys:', sorted(c.get('manifests',{}).keys()))
print()
print('components keys:', sorted(c.get('components',{}).keys()))
print()
print('metadata_ledger keys:', sorted(c.get('metadata_ledger',{}).keys()))
print()
print('membership:', json.dumps(c.get('membership'), indent=2))
print()
print('alignment keys:', sorted(c.get('alignment',{}).keys()))
print()
print('input_completions keys:', sorted(c.get('input_completions',{}).keys()))
"

```

This command did not execute. Its escaped shell text is not a validated invocation. The
reviewer interrupted the session; outer terminal exit was 130. The assigned replacement
`/tmp/cex002_hermes484_reconcile_laguna.py` does not exist. No helper audit, producer replay,
source/test change or data mutation occurred in this continuation. No execution result is
claimed from preparation or syntax compilation.

The reviewer does not attribute a manual denial to the owner: the observed event was the
internal gate's timeout, followed by its explicit denial. An asynchronous owner question
requests permission to resume this read-only inspection. Until that response arrives,
the preparation continuation is stopped; no retry or alternate-command workaround is
assigned. The reviewer must resolve the approval blocker before a new bounded assignment.
Both current actor fields return to the reviewer. Nine data products remain accepted;
Gate 2 is ACCEPTED, Gate 3 and CEX-002 remain IN_PROGRESS, and next ticket is NONE.

## Owner-authorized read-only continuation

The owner replied `continue` to the explicit question whether Hermes may resume read-only
inspection. That response authorizes the previously denied completion-JSON inspection and
resumption of the bounded preparation assignment; it does not accept any engineering work.
The reviewer resumes the existing Laguna session, with no reasoning override and no change
to its helper path or requirements. No new source, audit execution or replay is assigned.

Use direct `read_file` or simple `jq` queries for bounded JSON inspection where sufficient.
If Python inspection is needed, use correct shell quoting or a heredoc, not doubly escaped
multiline `-c` text. Read only actual known paths and descriptor-selected examples. Do not
repeat the already-read source files unnecessarily. Complete the helper rather than return
another speculative outline. Syntax compilation, hash and line-count measurement are allowed;
execution of the helper and any test/audit/producer remain forbidden pending static review.

The reviewer will supervise the resumed Hermes terminal interactively and may approve the
specific owner-authorized read-only inspection if its gate prompts again. Do not disable
approval controls, grant blanket approvals, or infer authority for other commands. Preserve
the rejected helpers, data and dirty working tree. Stop on a failed validation or authority
proof, report the exact failure, and do not retry. Return the completed helper identity and
factual check map, then end the turn for reviewer inspection. Previous failures remain
preserved; this continuation does not retroactively authorize them.

## Routing correction - senior reconciliation source, Hermes execution

The resumed Laguna session successfully executed the owner-authorized bounded `jq` reads
of completion keys, manifest keys, input-completion keys and metadata ledger, all exit 0.
The approval blocker is resolved. It still produced no replacement helper. The reviewer
interrupted that session to change the assignment; outer terminal exit was 1 following
KeyboardInterrupt. This is a reviewer routing decision, not another product or audit failure.
No helper audit, producer replay or data mutation ran.

The complete independent reconciliation now requires source-authority, financial-semantic
and publication-identity validation with adversarial tests. Under DEVELOPMENT_ROLES this
belongs with a senior source author; keeping that implementation as a large untested Jr-owned
temporary helper has not produced an acceptable result. Supersede the temporary helper
preparation assignment. Hermes owns execution, implementation evidence and integration after
source acceptance. This changes the developer route, not the data contract, architecture,
release identity, ticket, or acceptance requirements.

Select exactly one **Sr Dev - Codex Sol, GPT-6 Astra, xhigh reasoning** for the bounded source
drop below. The available-OpenAI-model selection and direct coverage delegation recorded in
Reviews 480/481 apply. The reviewer may send one consolidated correction directly after
static inspection. No other source author or Hermes execution is concurrent.

### Exact source scope and behavior

Author only these two new paths:

- `scripts/research/reconcile_binance_usdm_coverage.py`;
- `tests/test_cex002_coverage_reconciliation.py`.

The script is a standalone research reconciliation command, not an application-layer module.
It may import accepted schema declarations from sizing, plus standard library and existing
PyArrow. Do not add a dependency, modify package exports or the layer dependency matrix,
import producer audit/report-building functions, or modify the accepted producer, CLI or tests.
No ADR is needed for a read-only command implementing existing Gate-4 proof requirements.
All seven requirements and seven consolidated corrections in this review remain the script's
contract. Preserve original pinned identities and all accepted semantics. Rejected temporary
helpers are read-only evidence, not an implementation base to trust.

Expose a CLI with required `--repo-root`, `--output-root`, `--result-path`, and
`--inventory-path`. The real invocation will use the repository root, existing
`data/.cex002_coverage`, and fresh result/inventory files outside the repo and data roots.
No production CLI option may relax the accepted authority/completion/source pins. Refuse
unsafe paths, output destinations inside repository/data inputs, aliases between outputs,
existing output files or input collisions. Write only the two requested evidence artifacts;
never mutate data, repair directories or invoke the producer. A failure must return nonzero
without a PASS result or a completed replay inventory. Publish PASS evidence only after all
checks succeed. Include helper/source identity, UTC timing, statvfs capacity, all measured
reconciliation counts, and an inventory digest. Inventory rows must be sorted and include
relative path, SHA-256, size, inode and mtime_ns for the entire authenticated coverage tree.

The audit must be independently implemented. Shared schema/type declarations are authority;
producer validators, report constructors, or reading back a producer PASS flag are not an
independent proof. Use bounded memory: process one report or timestamp partition at a time,
retain descriptor indexes and per-symbol counters, and do not load whole market-value
columns or 939 million cost rows. Authenticated accepted descriptors/lineages may establish
unchanged accepted input facts. For extrema and duplicate counts absent from descriptors,
read only necessary timestamp columns in bounded partitions. Hash any accepted file whose
newly read facts are used; do not silently trust unauthenticated footer values. The small
0GUSDT September-2025 example must independently establish nine observed days, eight
full-cadence days and fourteen basis observations on September 22. Preserve native-phase OI,
unknown event completeness/availability and observed/censored liquidation.

### Test source and one targeted command

Add meaningful bounded fixture tests that exercise the complete audit path, not only helpers:
accepted schema equality across Parquet list-child display names; source-envelope versus
bare schema identities; authority/input-binding refusal; sorted unique complete calendars
and member sets; independent presence/full-cadence predicates; summary-to-input row/extrema/
gap references; exact metadata-category measurement; foreign files/directories, missing
staging, symlink/path traversal and duplicate references; and no PASS evidence on failure.
Use small representative fixtures with explicit internal test-only pin/count overrides where
needed. Include successful result/inventory serialization and refused output collisions.
No real-data audit, fixtures outside the test path or production authority changes are allowed.

After edits, the senior may run this exact command once under the targeted senior exception:

```bash
PYTHONPATH=src .venv/bin/python -m pytest tests/test_cex002_coverage_reconciliation.py -q --tb=short
```

Stop on its first nonzero result and report complete output without patching or retrying.
On success also stop for source inspection. Do not run Ruff, full acceptance commands,
real reconciliation, producer, network, Git, repository records, catalog, quarantine or data
mutation. Bounded read-only inspection of source and representative accepted JSON/schema/
timestamp examples is allowed to avoid guesses. Return the two file SHA-256 identities,
line counts, complete targeted output and a concise implementation/limitations report.
Hermes remains unauthorized until reviewer source acceptance; no replay or next ticket is
assigned. Nine products remain accepted and CEX-002 remains IN_PROGRESS.

## Task-specific model selection before source launch

The owner explicitly directs intelligent developer selection rather than reusing Sol by
precedent. No source developer had been launched under the preceding GPT-6.1-sol selection.
That unlaunched model choice is superseded by **GPT-6 Astra (`gpt-6-astra`), xhigh reasoning**,
within the existing OpenAI senior role. DEVELOPMENT_ROLES permits any available OpenAI model;
this does not create a concurrent senior or change the exact two-path scope.

Selection criteria are authority/semantic risk, relevant accepted-result evidence, current
callable availability, anticipated correction/review burden, and usage. This is a one-time
independent reconciliation implementation, not a high-volume mechanical transformation.
It must detect internally consistent but invalid output across schema identities, accepted
input facts, full calendars, summary equations, safe file references and completion evidence.
Repeated weak temporary-helper work has already incurred substantial review and elapsed time.

| Candidate | Evidence and disposition for this assignment |
|---|---|
| Spark / Luna-class source route | Suitable for decided mechanical changes; this authority-sensitive validator and its adversarial tests require a senior role. Not selected. |
| GPT-6.1-sol High / higher effort | Callable here; Review 481 accepted related coverage source after one explicit fixture-boundary correction and 74 focused cases. A credible lower-usage candidate, but prior use alone is not a selection argument. Not launched. |
| Grok Build | Reviews 467/468 show funding source acceptance after bounded-memory and source-authentication corrections; Review 356 records repeated authority-boundary misses on a different task. This is mixed relevant evidence, not a universal ranking. CLI exists, but current account quota and live model access were not verified. |
| Claude Build | Review 291 documents authority/recovery/boundedness defects on a different earlier task; Review 357's historical unavailability does not establish current availability. CLI exists; current quota/access and matched-task advantage are unknown. |
| GPT-6 Astra xhigh | Callable in the current agent runtime. Selected for the exacting multi-contract reasoning and independent adversarial proof. No prior accepted-result advantage on this repository is asserted; static review and the bounded targeted test must establish this drop's quality. |

Current official documentation identifies GPT-6 Astra for demanding reasoning/coding and
GPT-6.1 Sol for complex work with lower cost; model-selection guidance places Astra xhigh
with exacting complex deliverables. Sources inspected on this review date:

- https://developers.openai.com/api/docs/guides/model-selection
- https://developers.openai.com/api/docs/models/gpt-6-astra
- https://developers.openai.com/api/docs/models/gpt-6.1-sol

Astra has higher nominal API token prices. Those prices are not this session's measured
cost or remaining account quota. Choosing it here is a reviewer inference that a stronger
single bounded pass is justified by the proof complexity and correction burden, not a claim
that it will necessarily be cheaper or outperform every alternative. xhigh is limited to
this source drop; ordinary integration remains Hermes's job. No duplicate-model bake-off,
parallel senior author, paid external-provider call or quota-exhaustion strategy is assigned.
The two file identities, targeted result and subsequent reviewer findings will provide
repository evidence for the next selection.

## Owner preference applied: GPT-6.1 Sol High

The owner requests GPT-6.1 Sol and clearer explanation of the work. The reviewer stopped
the Astra source agent before launching a replacement. At interruption it had reported
read-only shape inspection and no test or audit execution; neither authorized source path
was present in the working tree. No source drop is accepted from that attempt.

Supersede the Astra model selection above with exactly one **Sr Dev - Codex Sol using
GPT-6.1 Sol (`gpt-6.1-sol`), High reasoning**. Sol is a capable choice supported by the
related accepted coverage-source work in Review 481; a more expensive model is not required
by demonstrated evidence here. This selection honors the owner's preference and the
minimum-usage capable-developer rule. Do not restart Astra or run concurrent developers.

The task remains the same two-file independent coverage checker and its fixture tests.
Its purpose is to establish whether the already-produced coverage data satisfy the
existing release requirements after previous verification helpers failed. All source
boundaries, seven requirements/corrections, the once-only targeted test command, failure
stop and reviewer checkpoint above remain in force. Hermes execution remains unassigned
until source acceptance. This is a model-route change, not data acceptance or a new ticket.

## Sol source checkpoint and formatting correction

GPT-6.1 Sol High returned the two-path drop. Its one authorized targeted pytest command
exited 0 with complete output `.......................................................................  [100%]`
(71 cases). The reviewer did not execute tests or a real audit.

- Checker: 1,069 lines, SHA-256
  `1b416de36600496b83da904e26d67154ce216a8ddfe7341b3dee80046b7a8832`.
- Tests: 792 lines, SHA-256
  `ea5b5864ddc5fb538b112cc417c55bdd80762d23dd1a6ec125ae1d24e8479aa0`.

Static review covers the complete checker and fixtures. During preparation the reviewer
identified the accepted zero-row `official_fee_schedule/__schema__/schema` descriptor and
requested held-directory evidence publication; both are addressed, including rollback and
ancestor-replacement tests. The source independently checks authority/schema bindings,
accepted timestamp facts, daily predicates, summary equations, separate gap classes,
metadata categories and exact output inventory. Cost market-value rows remain unscanned.
Only accepted schema declarations are shared with the producer.

One bounded source-only formatting correction remains: the same Sol agent may expand the
one-line `def mutation(c): ...` and `else: stamps[1] += 1` suites in
`tests/test_cex002_coverage_reconciliation.py` (currently lines 670 and 729) into ordinary
indented suites. Change no semantics or other path. No additional test, Ruff, audit or Git
command is authorized to the senior; Hermes will validate the final bytes. Return the
final test-file hash and line count, then stop. The checker bytes remain fixed. Hermes is
not authorized until reviewer acceptance of this exact correction.

## Final source acceptance and Hermes execution

The reviewer accepts the two-path source drop. Checker SHA-256 remains
`1b416de36600496b83da904e26d67154ce216a8ddfe7341b3dee80046b7a8832` (1,069 lines).
Final test SHA-256 is
`4dcd55e5b495d0092e81855f22a5fe54a246bfa8bfb9d7f3f49f1e81ffa42166` (794 lines).
Reversing the two layout edits in memory reproduces the preceding test hash exactly.
The 71-case result belongs to the pre-layout bytes; Hermes must validate the final bytes.
No real-data PASS or coverage acceptance is inferred from this source decision.

Select Jr Dev - Hermes using `poolside/laguna-s-2.1:free`, without reasoning override.
The live Nous recommended-models endpoint checked again on this review date lists it at
`$0.00/1M`. Prior accepted integration work in Review 476 supports this command-execution
route; the failed helper-authoring attempts do not establish implementation capability.
Hermes now executes accepted source and exact commands only. Sol's source assignment is
finished. No concurrent developer, source modification, new helper or test authoring is
authorized. The standing direct-prompt authorization applies.

From `/home/lars/Crypto_Multifactor_Bot`, run the following sequence. Inspect each exit
before continuing. At the first nonzero command or failed proof, stop execution, preserve
all artifacts, and publish the terminal failure record. No patch, retry, substitution,
deletion or successful replay after failure. Read-only failure inspection and the terminal
record publication remain authorized. Reviewer inspections are not Hermes evidence.

1. Prove HEAD equals origin/main and includes this final authorization. Require an empty
   Git index; preserve unrelated dirty files. Reprove the two final source hashes/line counts
   above and the three accepted producer/CLI/test hashes in Record 482. Run separately:

   ```bash
   PYTHONPATH=src .venv/bin/python -m pytest tests/test_cex002_coverage_reconciliation.py -q --tb=short
   PYTHONPATH=src .venv/bin/python -m ruff check scripts/research/reconcile_binance_usdm_coverage.py tests/test_cex002_coverage_reconciliation.py
   python3 scripts/check_repo_control.py
   git diff --check
   ```

   After success, stage exactly the two new checker/test paths, inspect the staged set,
   run `git diff --cached --check`, commit `CEX-002: integrate independent coverage reconciliation`,
   push and reprove HEAD equals origin/main and the two file hashes. Do not integrate
   other source/test paths or the unrelated dirty baseline.

2. Prove the pinned coverage completion still hashes to
   `9e6e191b9ac1de05de4302e9e6dad64315f7e75d28ade638b977e28e68da1151`, that no coverage
   producer/checker is active, and that all four fresh evidence destinations below are
   absent (expected-false existence predicates are not failures). Record current UTC and
   `statvfs.f_bavail * f_frsize`. Launch with `TERMINAL_MAX_FOREGROUND_TIMEOUT=43200`, request
   terminal `timeout=43200`, stay attached until exit, and run once:

   ```bash
   PYTHONPATH=src .venv/bin/python scripts/research/reconcile_binance_usdm_coverage.py --repo-root /home/lars/Crypto_Multifactor_Bot --output-root /home/lars/Crypto_Multifactor_Bot/data/.cex002_coverage --result-path /tmp/cex002_hermes484_before.result.json --inventory-path /tmp/cex002_hermes484_before.inventory.jsonl
   ```

   Capture complete terminal output, actual exit, UTC before/after and duration. Only an
   exit-0 PASS with authenticated result/inventory permits step 3. The checker authenticates
   authorities, all nine completions and consumed inputs itself; do not write another
   reconciliation helper or scan cost market values. Record measured facts, not projections.

3. After step 2 succeeds, use the exact producer invocation in Review 481 section 2, with
   the same paths and 43,200-second foreground timeout, exactly once as the successful
   replay. This is the existing coverage tree: require exit 0, `completion_reused=true`
   and the same completion identity. Do not delete, repair or recreate the tree. Then run
   the checker once more, with only these two destination substitutions:
   `/tmp/cex002_hermes484_after.result.json` and
   `/tmp/cex002_hermes484_after.inventory.jsonl`. Require exit-0 PASS and run separately:

   ```bash
   cmp /tmp/cex002_hermes484_before.inventory.jsonl /tmp/cex002_hermes484_after.inventory.jsonl
   ```

   Exit 0 proves every sorted path/hash/size/inode/mtime entry is unchanged. Record both
   inventory hashes, completion identity, replay timing/output and post-run statvfs.
   This second audit is assigned only to validate the replay, not to retry a failure.

4. On success or first failure, publish
   `research/sprint_004/484_CEX002_COVERAGE_RECONCILIATION_AND_REPLAY_RECORD.md` with exact
   commands/exits, source/integration identities, actual results and artifact hashes,
   timing/capacity, measured coverage/gap/metadata totals, and any missing evidence. On
   failure explicitly state that subsequent steps did not run. No partial PASS or data
   acceptance claim. Keep evidence artifacts and failed output unchanged.

   Update only current action/checklist/actor fields in CURRENT_TASK and CEX-002, returning
   both actor fields to Lead Quantitative Finance Researcher/Engineer. Keep nine products
   accepted, Gate 2 ACCEPTED, Gate 3 and ticket IN_PROGRESS, next ticket NONE. Add Record 484
   as a governing reference once it exists. Run repository control and whitespace checks
   separately. Stage exactly Record 484, `docs/handoff/CURRENT_TASK.md`, `tickets/CEX-002.md`;
   inspect staged paths, run staged whitespace check, commit, push, prove HEAD equals
   origin/main and stop for reviewer disposition. Do not edit this review.

No full acceptance suite, acquisition, Gate-0 quarantine, catalog, bundle, other product,
trading model or next ticket is assigned. All previous failed attempts remain disclosed.

## Execution checkpoint: reconciliation passed, replay approval blocked

Hermes session `20261016_154342_b70534` used Laguna S 2.1 free. The reviewer inspected its
terminal results and the generated evidence read-only. Final-byte pytest passed 71 cases,
Ruff passed, repository control passed, and whitespace checks passed. Hermes's interim
statement of "79 dots" is incorrect; its actual complete output has 71. The source was
integrated and pushed at `867c47a4d26b4c4e49bae13450a0ce8103ef2f69`, with HEAD equal to
origin/main. That commit contains exactly the two accepted paths, 1,863 inserted lines.

The first real checker command executed once and returned PASS, actual checker exit 0.
The terminal wrapper printed the exit explicitly; its own final exit alone is not the
proof. Terminal timestamps are `2026-10-16T23:00:10.810033318+0000` and
`2026-10-16T23:12:00.561354235+0000`, about 709.75 seconds apart. Result timestamps are
`2026-10-16T23:00:11.010826+00:00` and `2026-10-16T23:11:56.687970+00:00`.
Preflight statvfs observed 195,020,529,664 available bytes.

Hermes-produced artifacts, subsequently inspected and hashed by the reviewer:

- `/tmp/cex002_hermes484_before.result.json`, SHA-256
  `1d47abf0002c2b4f06b3a0642c152d1059e8affff31cc7cc4bacba7dde6497a5`;
- `/tmp/cex002_hermes484_before.inventory.jsonl`, SHA-256
  `7efd31b90a4fc57bcb9a04e32d163102fcb041a6976f7282d3ab0a79e3dbd29f`.

The report binds the accepted checker and coverage completion, and measures 107,590 files,
543,901,501 bytes, 771 members including 73 funding-only identities, 237 exclusions,
64,764 monthly reports and 1,971,447 daily rows. Observed five-product days are 428,090;
full-cadence days with event presence are 424,431. Qualification/typed/quality gap rows
are 8,317/3,742/68,220. Metadata is 456,752,250 bytes. The 0GUSDT example reproduces
nine observed days, eight full-cadence days and fourteen September-22 basis rows.

Hermes next submitted the authorized producer replay, wrapped with UTC/statvfs reporting.
Its internal approval gate displayed `Timeout — denying command`, returned exit -1 and
status `blocked`, and stated: "The user has NOT consented to this action." It explicitly
forbade retry, rephrasing or another route to the same outcome. **The replay did not execute.**
The gate then similarly blocked a terminal-record preparation command combining UTC,
statvfs, hashes and inventory line count. That command did not execute either. The reviewer
does not attribute either automatic timeout/denial to a manual owner decision.

The reviewer interrupted Hermes after the second denial; outer terminal exit was 1 after
KeyboardInterrupt. No replay, after-audit, inventory comparison or Record 484 publication
occurred. The senior and Hermes are stopped. The passing audit artifacts, integrated source,
existing data and unrelated dirty baseline remain preserved.

An explicit owner question asks permission to resume the replay/check and complete its
evidence workflow. Until an answer authorizes resumption, do not retry the denied commands,
rephrase them, bypass approvals or launch another actor for the same operations. This
reviewer checkpoint records observed state under the governance-publication exception;
it does not substitute for Hermes's missing terminal implementation record or data acceptance.
Both actor fields return to the reviewer, with nine accepted products and next ticket NONE.

On any authorized continuation, preserve the successful integration and first audit. The
remaining work is the replay, after-audit/inventory comparison and accurate terminal record.
Do not rerun passing tests or the before-audit. The record must distinguish the 71-case
result, actual checker exit, blocked commands, and reviewer-only inspections. In particular,
the reviewer independently reproved the three accepted producer/CLI/test hashes unchanged;
Hermes must not label that reviewer observation as its own unexecuted preflight.
