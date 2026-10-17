# CEX-002 Review 489 — Bounded one-minute/hourly reconciliation source

Reviewer: Lead Quantitative Finance Researcher/Engineer
Ticket: CEX-002 (IN_PROGRESS)
Source actor: Sr Dev — Grok Build (grok-4.7 High)
Next ticket: NONE

## Decision and routing

The owner reports that Grok has almost all of its usage remaining and that access ends
tomorrow night. Prioritize substantive Grok implementation under the existing CEX-002
completion order. Grok completed the strict BitMEX correction; its six approved paths
are integrated and pushed at f85177d9f1d21fe1fd054d40035afbf62b4e457f. The reviewer
independently matched committed blobs, staged blobs and worktree hashes. Hermes passed
52 targeted cases, Ruff, repository control and source/staged whitespace checks.
Technical source integration is accepted. Record 488 publication and final Gate-0
disposition were still in progress when this disjoint source assignment began. Hermes
has now published Record 488 at 68e93069acfdaa0a2fc9d7d606f75feaa4fcd49f, and Review 487
accepts Gate 0. Its extra malformed Git-object probe and post-failure inspection remain
disclosed. No source repair or accepted-product rerun is warranted by those record errors.

Authorize Grok now for the independent source-only assignment below within the SAME
active ticket. This does not wait for administrative Record 488 publication. There is
one senior source actor; Hermes performs only the previously assigned record publication.
The reviewer reconciles the current-task header after Hermes returns it. Neither
actor may stage the other's paths. This assignment implements the missing bounded
one-minute/hourly comparison in Gate 4 and Review 474; it does not accept Gate 4 or the
bundle, and does not introduce a new product, acquisition generation or architecture.

## Five writable paths

- `src/cryptofactors/acquisition/binance_usdm_kline_comparison_sample.py`
- `src/cryptofactors/ingest/binance_usdm_kline_reconciliation.py`
- `scripts/research/reconcile_binance_usdm_klines.py`
- `tests/acquisition/test_binance_usdm_kline_comparison_sample.py`
- `tests/ingest/test_binance_usdm_kline_reconciliation.py`

Existing source, exports, schemas, dependencies, catalogs, data and records are read-only.
No installations, real downloads, real comparison runs, Git, commits, pushes, cleanup,
archive access or developer evidence publication. Use normal CLI approvals. Author all
test fixtures inside test source and temporary directories. No other senior is assigned.

## Fixed authorities and sample selection

Read the existing contracts in CEX-002 Gates 4-5, Review 474, ADR-0024/0025/0035, and the
accepted hourly schemas/normalizer. Do not reread historical ticket narratives. Relevant
references are `binance_usdm_klines.py`, the sizing module's final product schemas,
and the descriptor/authentication patterns in `reconcile_binance_usdm_coverage.py`.

Pin qualification report `research/sprint_004/62_CEX002_GATE1_SOURCE_PROCUREMENT.json`
at SHA-256 `f27b2ba7e6eff3a8b1385d985c49ee64ef60a394737b1246130d0f37b9015f09`.
Select its **daily/klines, 1h** sample records only. These are ten role bindings and nine
distinct symbol/days; preserve the duplicate recent/delisted role without downloading twice:

| Symbol | Early | Middle | Recent | Delisted role |
|---|---|---|---|---|
| 0GUSDT | 2025-09-17 | 2026-03-21 | 2026-05-30 | none |
| 1000BTTCUSDT | 2022-01-26 | 2022-03-12 | 2022-04-11 | 2022-04-11 |
| KAIAUSDT | 2024-12-04 | 2025-10-25 | 2026-07-19 | none |

The expected comparison ZIP for each row is exactly
`data/futures/um/daily/klines/{symbol}/1m/{symbol}-1m-{date}.zip`, and its official
`.CHECKSUM` sibling, under `https://data.binance.vision/`. No listing, arbitrary URL,
alternative symbol/day, full one-minute history, or substitution is permitted. These
comparison inputs do not amend generation 0 or replace selected hourly raw sources.

Pin accepted hourly completions (read only):

- bar root `data/.cex002_bar_1h`, completion
  `3b803d3e84e5d0bf87064626cc0504e9ff92e225a53ba83cdd4e09c38a2e9fd7`;
- flow root `data/.cex002_trade_flow_1h`, completion
  `a165f9e57065514cadc95620c280a82dbad5032d17c19e1caf012c9d12a84d0a`.

Authenticate the completion and only its selected symbol/month descriptors, Parquet
hashes/schemas/row counts and lineage; do not rerun full-product audits or normalize any
accepted product. Bound row memory to one selected day plus one selected monthly
partition. Production CLI cannot override identity hashes, symbols, dates or schemas;
private test fixtures may inject a small policy without becoming a production bypass.

## Acquisition boundary

The acquisition module alone owns HTTP. Implement a callable bounded sample fetcher;
the reconciliation module stays offline. The CLI must require explicit `--fetch` for
network activity, and otherwise authenticate and reuse already retained sample evidence.
Grok must not invoke `--fetch` or any real run. A later Hermes assignment will name the
actual evidence root and execution command after source review.

Use existing dependencies and publication patterns. Enforce nine ZIPs maximum, 8 MiB
compressed per ZIP, 16 KiB per sidecar, 128 MiB decompressed per ZIP, one expected CSV
member, and at most 1,440 data rows/day. Enforce limits while streaming, regardless of
Content-Length. Bound request timeouts; no implicit unbounded retry or alternate source.
Reject redirects outside the exact official object, non-success HTTP, malformed/mismatched
checksum statements and filename, truncated ZIP, unsafe members, CRC failure, and path
escape/symlink destinations. Do not extract archive members onto the filesystem.

Retain exact ZIP and sidecar bytes with their hashes, source keys/URLs, byte sizes,
retrieval times, and source availability explicitly unknown. Use a caller-selected
isolated evidence root with immutable content-addressed files, same-directory temporary
publication, fsync/no-clobber, and a last-written complete sample manifest. Reuse only
after reauthentication; partial interrupted work must not appear complete. Conflicting
retained evidence fails; do not overwrite or repair it silently. Keep protected report,
accepted product and generation-0 roots read-only; reject overlapping evidence outputs.

## Independent economic comparison

Parse headed/headerless twelve-field Binance kline rows strictly. Require exact integer
millisecond times/counts, UTC day ownership, 60,000-ms opens and close=open+59,999;
finite exact decimal tokens representable by the accepted scale-18 contract, correct
OHLC ordering, nonnegative volumes/counts and taker values within totals. Do not call the
hourly normalizer to produce expected results. Aggregate with exact scaled integers so
ambient Decimal precision and binary floats cannot alter sums or comparisons.

Sort by native timestamp, collapse only identical duplicates with explicit counts, and
reject conflicting keys. Only a complete hour of 60 distinct native minute slots may
produce a comparable hourly observation. Missing/partial hours remain explicit gaps;
never fill a slot, stretch a period or infer a zero. Every parsed row must reconcile to
a compared hour, an identical duplicate or an explicitly uncomparable hour.

For a complete hour, independently compute first open, maximum high, minimum low,
last close, sums of base/quote volumes, integer trade counts, and taker-buy base/quote
volumes. Compare each applicable field exactly with the accepted bar and flow rows.
Recompute flow's sell volumes as total minus buy, and its imbalance fields according
to the frozen schema's existing equations (inspect the implementation to identify the
published quantity, do not assume a normalized ratio). Preserve signed/zero derived
values; a zero is valid only when supported by observed source rows. Compare by
symbol and exact open/close times, not row positions.

Honor ADR-0035's product-specific quality exclusions: a missing accepted row must be
explained by its authenticated quality-gap evidence, never synthesized from minutes.
Do not extend those exclusions to hide a new minute-source defect or a cross-interval
mismatch. Record the exact source tokens/ordinals and compared product values for each
discrepancy. A discrepancy returns nonzero and a durable FAILED evidence report; it
does not modify accepted data or automatically revoke earlier product acceptance.

An authenticated day with no comparable hour, an unexplained absent hourly row, missing
sample/role, failed input proof, or any unequal comparable field cannot yield PASS.
Require at least one successfully compared hour in every distinct sample day and every
early/middle/recent/delisted role. Partial boundary hours may be honestly reported as
uncomparable alongside successful full hours; do not relabel bounded sample success as
full-history reconciliation. Keep per-day/hour/field counts and explicit denominators.

Publish a deterministic, content-addressed comparison report plus a small completion
reference only after validation. Bind report/sample/product/source/code/config identities,
exact comparisons, gaps, mismatch counts and arithmetic policy. Real retrieval timestamps
remain in retained sample receipts; replay over identical retained inputs reuses byte-
identical evidence. No catalog transaction, bundle publication or invented source clock.
Failure must return nonzero without a successful completion marker. Read-only replay
must authenticate prior evidence rather than trust an existing PASS label.

## Tests and one targeted execution

Author meaningful temporary-fixture tests for sample-role deduplication and exact selection;
mock HTTP/checksum authentication, bounds, malformed/truncated/unsafe ZIP, redirects;
no network without explicit fetch; corrupt retained evidence and interrupted/no-clobber
resume; headed/headerless minute parsing, timestamp units/day/close alignment, exact
decimal sums and low ambient precision, shuffled/identical/conflicting rows, partial
hours, required-day/role coverage, product-specific quality gaps, differing row orders,
each comparison field and imbalance mismatch, missing/stale/wrong completion/schema/
lineage/hash, protected output paths, deterministic replay and FAILED-not-PASS behavior.

Under the targeted senior test exception, after the complete five-path drop is ready,
Grok may run exactly once:

```bash
PYTHONPATH=src .venv/bin/python -m pytest tests/acquisition/test_binance_usdm_kline_comparison_sample.py tests/ingest/test_binance_usdm_kline_reconciliation.py -q --tb=short
```

Stop on the first nonzero result; report exact output without repair/retry. No additional
syntax checks, Ruff, acceptance suite or real CLI execution. Return the five paths with
SHA-256/line counts, targeted result and limitations, then stop for reviewer inspection.
Source authoring does not accept real sample evidence. Integration, later real execution
and evidence remain separately bounded after source review. Existing ten accepted
products, holdout 2026-08-21T16:19:08.994166+00:00 and next ticket NONE remain unchanged.

## Reviewer publication scope

The reviewer may publish exactly this review, Review 487's final acceptance section,
`docs/handoff/CURRENT_TASK.md` and `tickets/CEX-002.md`. Wait for Hermes's three-path
Record 488 publication before staging reviewer governance, to avoid shared-index races.
Grok may author its five disjoint source paths while that record-only work finishes.

## Source supervision — implementation in progress

Native Grok Build session `01a14b01-adae-7ce2-83b5-ed5851be7d9d` is the sole
senior source actor. During preparation it requested an unassigned Python calendar /
PyArrow-Parquet roundtrip probe. The reviewer denied that command before execution;
it produced no test result. Because denial ended the native turn, the reviewer explicitly
continued the same five-path assignment in the same session, directing incremental
source writing and preserving the one targeted pytest command above. This was not a
model rotation or authorization for further exploratory executable probes.

The acquisition module, offline reconciler and subsequent scoped edits have been written.
The CLI/test files and targeted result are still pending. No source acceptance,
integration, real sample acquisition, or comparison evidence is claimed by this update.

### In-progress static feedback

Before the first targeted test, address these concrete issues within the same five paths:

- `load_sample` validates manifest records against themselves rather than reading their
  physical receipts. Authenticate the receipt file, its content-addressed name and its
  exact agreement with the manifest; reject missing, corrupt or conflicting receipts.
  Recheck the retained sidecar SHA-256 when consuming minute rows, as for the ZIP.
- `_aggregate_day` iterates only hours containing rows. Report all 24 native UTC hours
  of each selected day, including zero-observation hours, with explicit expected /
  observed slot denominators. This does not require filling gaps or rejecting an otherwise
  valid bounded sample solely for partial boundary coverage.
- `_compare_hour` can accept an authenticated quality exclusion without recording it in
  the result. Emit each skipped product/hour with its reason and authenticated evidence
  reference, plus per-product/field comparison denominators. Preserve the distinction
  between observed minute rows, excluded hourly products and successfully compared values.

Include focused regression cases for these behaviors. The original single targeted test
authorization remains unchanged; this feedback grants no additional command or retry.

For applying these source edits, the reviewer inspected and authorizes the temporary
editing helper `/tmp/patch_cex002_489.py` and its single execution with
`python3 /tmp/patch_cex002_489.py`. It performs exact-string edit preconditions and writes
only the assigned acquisition and reconciliation modules. It imports no project code,
runs no tests or application logic, and touches no data or repository records. The
temporary helper is not part of the source drop or integration. This explicit editing
allowance does not expand the production/test paths or the targeted-test authorization.

The helper was not created or executed: delivery of queued reviewer guidance canceled
that pending tool call. Queued static feedback and a repeated instruction to write files
also canceled pending direct-edit batches before execution. The native tool results
reported `user_cancel`; these were supervisor message-delivery interruptions, not test
failures or a developer refusal to produce code. Existing files remained intact. The
reviewer now lets the same Grok session finish the edits without further queued messages.

Grok subsequently submitted the same bounded replacement operation directly as a
`python3` heredoc, without creating the temporary helper. The reviewer inspected its
entire command and authorizes that source-edit operation: it reads/writes only the two
assigned modules and checks replacement preconditions; it executes no project code or
tests. Normal single-command approval applies. This is the source-edit alternative to
the unused temporary helper, not an additional validation command.

The inline source-edit command exited 0 and applied the three corrections. Grok then
wrote both test files and submitted the exact targeted pytest. The reviewer accidentally
selected rejection in the native command approval menu; the native result says
`User rejected the execution for tool run_terminal_command`. The test did not execute,
so there is no failing or passing result from that submission. The reviewer explicitly
reauthorizes submission of the identical targeted command; the allowance remains one
actual execution, followed by a stop on its first nonzero result.

## Complete drop review and bounded correction

The identical targeted command subsequently executed once and exited 1. Its progress
line was `.........F.....................................F..... [100%]`; the two failures
were `test_unsafe_zip_members_are_rejected` (the expected encrypted-member error was
not raised) and `test_structural_minute_failures_raise_and_gaps_do_not_hide_them`
(expected outside-day error, received minute-alignment error). Grok correctly stopped,
reported the exact output, and made no repair or retry. No integration is accepted.

The reviewer inspected the complete five-path drop. The three earlier production
corrections are present. Exact arithmetic, product completion/partition/lineage proof,
quality-gap provenance, deterministic publication and CLI fetch gating pass static
review. Following the owner's direction to reduce overhead, the immediate correction
is bounded to the two failing test fixtures and the statically visible fixture defects
listed below, in these two paths:

- `tests/acquisition/test_binance_usdm_kline_comparison_sample.py`
- `tests/ingest/test_binance_usdm_kline_reconciliation.py`

Keep the acquisition module frozen at SHA-256
`5f90aed17a483d29cbb17116250161f0412d8de8af5769e2a3a374d0f06b3f31`
(1,095 lines), and the CLI at
`e036f914797addca42cef88c77602744c368219ae6acdab57c5f7b8d9219751a`
(65 lines). The first tested reconciliation source is
`a175a34e9864d37502641f0dbe652844b464410773a9d0541c22c135a219ed48`
(1,134 lines); its test is
`f9b2e815d3e032a9cf4fa2d24506cf3e4b6e0d0be12b528d7c47a8acfd962d04`
(1,108 lines). The acquisition test is
`22c2637f482ae2dc4ae61f9336ad8a06f75b5e95db943983b2ab68653ef87b22`
(595 lines).

Grok remains the selected senior and must address this consolidated list:

1. Correct the encrypted-ZIP fixture. Python's ZIP writer clears a preassigned
   `ZipInfo.flag_bits`; construct bytes with the encryption flag actually present in
   both applicable headers and assert the fixture property before exercising rejection.
   Preserve the independent CRC and unsafe-member cases.
2. Isolate every malformed-minute case. The helper currently reuses a directory based
   on the first word of the expected error, so multiple `minute ...` cases reuse the
   first retained sample. Use independent fixture directories or parametrization.
   Correct the later `_minute(..., volume=...)` and
   `_minute(..., taker_buy_volume=...)` calls to its declared token-dictionary interface.
   Every specified failure must reach the production parser, not fail in fixture setup.
3. Remove the unused local `extra = dict(document)` in the selection test. This is a
   statically visible lint defect; no Ruff command has been run by the reviewer.

The reviewer withdraws the proposed extra test expansion from this immediate correction.
The previously noted prior-day object lifetime remains a source-review observation,
not an additional instruction to Grok in this fixture correction. Production is frozen.

After these edits, Grok is newly authorized to execute the same enumerated targeted
pytest command exactly once. The previous execution's failure is preserved; this is a
reviewer-authorized corrective execution, not an automatic retry. Stop on its first
nonzero result and return the exact output. No syntax/AST probes, Ruff, acceptance
suite, real run, data, integration, Git or record changes are assigned. All other
paths remain frozen, and next ticket remains NONE.

## Corrective targeted result

Grok fixed the two fixtures and the unused local, then executed the authorized
corrective command once: exit 0, all 53 cases passed. The production files retained
their hashes above. Final acquisition test: 600 lines, SHA-256
`562a45b459d093872e529fafc9c8ccb9418cdf53ca8111db431b8b1c84d1a295`.
Final reconciliation test: 1,111 lines, SHA-256
`a008bb38c0aee5940b92e698885c6a8d64154763c8bf24f020fc94cb8036a64c`.
The reviewer independently read the changed fixture sections and fingerprinted all
five files; the reviewer did not execute tests. The bounded fixture correction is
complete. No further Grok command, integration or real-data run is assigned. Control
returns to the reviewer for source disposition and integration planning; the earlier
source-memory observation remains explicit. CEX-002 remains IN_PROGRESS, next NONE.

## Final source decision and complete integration workflow

The reviewer accepts the five frozen paths above for integration. The prior-day
object-lifetime observation is a bounded resource limitation, not a release blocker
for these nine fixed samples: parsed minute objects can overlap for two days (at most
2,880 rows), with a fixed selected-hour cache and one partition read at a time. The
reviewer explicitly relaxes this assignment's one-day transient-lifetime target to
that two-day bound. Input byte/row caps and the nine-object limit remain enforced.
This narrow tool does not acquire full minute history or change the product architecture.
The owner directs reduced overhead; no additional source correction or test expansion
is warranted. The 53-case targeted pass and final hashes remain the source evidence.

Jr Dev — Hermes, using Nous `meituan/longcat-2.5-preview:free` with no reasoning
override, owns the following complete workflow. Selection uses its most recent accepted
52-case source integration and current native availability; earlier record errors stay
disclosed. Use normal interactive approvals. Stop on the first nonzero command,
denial, identity mismatch, or unexpected state; record the result without repair/retry.
No source/test edits, test design, package installation or additional helper is assigned.

1. Read this section, the current-task header and ticket's current checklist. Verify
   `HEAD == origin/main == c8a415266f47595381572f1d5040f99c439203ad`, empty index,
   and the five final hashes above. Preserve all unrelated dirty/untracked files.
2. Run these standalone checks, in order, each once:

   ```bash
   PYTHONPATH=src .venv/bin/python -m pytest tests/acquisition/test_binance_usdm_kline_comparison_sample.py tests/ingest/test_binance_usdm_kline_reconciliation.py -q --tb=short
   PYTHONPATH=src .venv/bin/python -m ruff check src/cryptofactors/acquisition/binance_usdm_kline_comparison_sample.py src/cryptofactors/ingest/binance_usdm_kline_reconciliation.py scripts/research/reconcile_binance_usdm_klines.py tests/acquisition/test_binance_usdm_kline_comparison_sample.py tests/ingest/test_binance_usdm_kline_reconciliation.py
   python3 scripts/check_repo_control.py
   git diff --check -- research/sprint_004/489_CEX002_BOUNDED_KLINE_RECONCILIATION_SOURCE_REVIEW.md docs/handoff/CURRENT_TASK.md tickets/CEX-002.md
   ```

3. Stage exactly the five accepted source/test paths plus this reviewer-authored review,
   `docs/handoff/CURRENT_TASK.md` and `tickets/CEX-002.md`. Confirm exactly those eight
   paths are staged, run `git diff --cached --check`, commit with message
   `CEX-002: integrate bounded minute-hour reconciliation`, and push `origin main`.
   Verify HEAD and origin/main agree. The reviewer authorizes publication of its three
   governance files with this source integration, avoiding a separate publication handoff.
4. Prove both `data/.cex002_kline_comparison_sample` and
   `data/.cex002_kline_reconciliation` are absent, `data/` is a real directory, and at
   least 1 GiB is available. Then execute this command once in the foreground, allowing
   up to 20 minutes, and remain attached through its terminal result:

   ```bash
   PYTHONPATH=src .venv/bin/python scripts/research/reconcile_binance_usdm_klines.py --repo . --evidence-root data/.cex002_kline_comparison_sample --output-root data/.cex002_kline_reconciliation --fetch
   ```

   Only this bounded fetch is authorized: nine exact official ZIP/CHECKSUM pairs. No
   alternative dates, full-history acquisition, accepted-product conversion, catalog
   mutation or source repair. A nonzero result ends real execution; preserve its evidence.
5. On success, inspect the sample manifest, comparison report and completion read-only.
   Record their content hashes, nine distinct days, ten roles, per-day compared hours,
   expected/observed slot counts, exclusions/gaps and zero mismatch/coverage-failure
   counts. Check report and completion names agree with their bytes and references.
   Preserve the completion/report identities. Run one offline replay:

   ```bash
   PYTHONPATH=src .venv/bin/python scripts/research/reconcile_binance_usdm_klines.py --repo . --evidence-root data/.cex002_kline_comparison_sample --output-root data/.cex002_kline_reconciliation
   ```

   Confirm the same manifest/report/completion hashes. No extra replay or whole-product
   audit is assigned; the CLI reauthenticates the selected retained inputs and products.
6. Publish `research/sprint_004/490_CEX002_KLINE_RECONCILIATION_INTEGRATION_AND_RUN_RECORD.md`
   with exact commands, outputs, exit codes, source/integration identities, real counts,
   replay identities and any failure/denial. Update the current-action summary in
   CURRENT_TASK and the existing ticket summary; return the actor to the reviewer.
   Keep CEX-002 IN_PROGRESS, next NONE and ten products accepted. Run repository control
   and whitespace over these three record/control paths, stage exactly those paths,
   confirm the staged list, check cached whitespace, commit
   `CEX-002: record bounded kline reconciliation result`, push, and verify HEAD equals
   origin/main. On an earlier execution failure, skip remaining tests/run/Git steps and
   publish the terminal failure through this same bounded record workflow only.

Reviewer acceptance of the real comparison remains separate from source acceptance.
The remaining release work stays the existing bundle, consumer readback and final checks.

Dispatch status: the sandboxed Hermes startup could not resolve network hosts. A request
to launch the native interactive agent with network access was rejected by automatic
approval review before launch, citing broad publication/download capabilities without
explicit owner authorization at launch. No assigned integration/check/download command
has executed. The owner has been asked to approve the bounded workflow above; source
acceptance and the existing 53-case pass remain valid. Do not bypass the rejection.

The owner subsequently manually approved the exact native Hermes launch with this
model/provider and repository working directory. Dispatch may proceed under that
approval and the bounded workflow above; unrelated actions remain unauthorized.

The approved launch succeeded in Hermes session `20261017_134003_4ecfbf`. Automatic
review separately rejected delivery of the full workflow prompt because manual approval
covered the launch only. A safer, local-validation-only prompt was accepted: read-only
identity proof, targeted pytest, scoped Ruff and repository control, then stop/report.
It authorizes no source/record edits, Git mutations, publication, download or real run.
Those steps remain pending explicit approval; do not infer them from launch approval.

Hermes completed local validation: all 53 targeted cases passed, scoped Ruff passed,
and repository control passed. It rehashed the five files afterward with all identities
unchanged and no staged changes. Native session export
`/tmp/cex002_review490_hermes_06.jsonl` retains the commands/results. Hermes appended
`echo EXIT:$?` to each check; each printed `EXIT:0`, independently preserving the check's
successful status. The control command included a trailing `.` and returned PASS.
These successful checks are preserved without rerun. Publication, real acquisition,
comparison/replay and Record 490 remain pending explicit owner approval of that scope.

The owner has now manually approved delivery of the exact full-workflow Hermes prompt
and answered yes to the remaining publication/comparison/replay work. Continue the
workflow with its outstanding documentation whitespace check, then step 3 onward.
The completed identity proof, 53-case pytest pass, scoped Ruff and repository-control
PASS satisfy steps 1-2: preserve them, do not repeat them. All other bounds and the
first-failure stop remain in force. This continuation grants no source/test repair.
