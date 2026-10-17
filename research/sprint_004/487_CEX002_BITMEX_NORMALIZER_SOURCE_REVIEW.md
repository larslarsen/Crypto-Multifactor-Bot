# CEX-002 Review 487 — BitMEX normalizer and publication correction

Reviewer: Lead Quantitative Finance Researcher/Engineer
Ticket: CEX-002 (IN_PROGRESS)
Next required actor: Jr Dev — Hermes (meituan/longcat-2.5-preview:free)
Next ticket: NONE

## Accepted baseline and routing

Review 485 accepts the exact-five quarantine/resolver source, real application, replay and
Record 486 at 4ff8bf4. Reviewer acceptance is published at 39e400e. Ten Binance products
remain accepted. This assignment closes the separate Gate-0 normalizer/publisher defect;
it does not rerun quarantine or accepted Binance work or accept the entire gate/ticket.

Select Grok 4.6 High for one bounded corrective source drop. Source authority, conflicting
financial observations and durable resume state require a senior actor. The owner expressly
invited Grok Build usage with expiring subscription capacity. Grok just completed the bounded
quarantine execution successfully, although that is execution evidence, not proof of this
new source's correctness. Its earlier source corrections remain adverse routing evidence;
review the result independently. GPT-6.1 Sol's accepted quarantine drop remains frozen.
The preceding owner integration exception was discharged and does not cover this assignment.
Grok now owns source/test source only, with the one targeted-test exception below. Hermes
retains subsequent integration/evidence/Git ownership; no Hermes execution is assigned yet.

The reviewer has preserved all five existing dirty/untracked BitMEX draft paths byte-for-byte
under `/tmp/cex002_review487_preserved_source/`, with `inventory.json`. These rejected drafts
are not accepted source. The exact paths below may now be corrected/replaced, retaining that
snapshot. Other dirty/untracked files, accepted quarantine code, all databases and existing
data/manifest/report artifacts remain untouched.

## Exact writable source paths

1. `src/cryptofactors/ingest/bitmex_funding.py`
2. `src/cryptofactors/ingest/__init__.py` (minimal public export only)
3. `scripts/research/backfill_bitmex_funding.py`
4. `tests/ingest/test_bitmex_funding.py`
5. `tests/ingest/test_bitmex_funding_backfill.py` (new focused failure-path tests)
6. `tests/ingest/fixtures/bitmex_funding_source_shapes.json`

No other source, schema, migration, dependency, configuration, governance or evidence edits.
No installations, archive access, graph generation, real HTTP/data runs, background jobs,
Git mutations, commits or pushes. Normal approval checks stay enabled. Read only relevant
repository files and this assignment; avoid broad discovery and historical record rereads.

## Findings and fixed correction contract

1. The draft converts arbitrary types to rates, symbols, intervals and integer times; raw
   payloads can be mistaken for already-normalized records. Make the API response boundary
   explicitly raw. Require source camelCase rate/daily-rate/interval fields there; do not
   rescue missing fields through normalized aliases. Mixed contradictory aliases fail.
   Normalized input support stays explicit and validates all eight schema fields. Require
   real nonempty string symbols/intervals, numeric finite non-boolean rates, valid aware event
   times, and integer non-boolean microsecond values where supplied. Validate event ISO and
   integer time consistency. Preserve subsecond timestamps without float round-trip loss.
   Unknown availability stays null; never derive availability from event time. Keep the
   existing eight-column Arrow schema and cashflow/provider behavior outside this defect.
   No invented daily rate, rate zero, interval or provenance. Raw source is bitmex_funding;
   normalized provenance must agree. Existing parse helper uses elsewhere may keep their
   contract; enforce the strict funding boundary separately if necessary.
2. Validate the entire table before publication, including daily rates, keys, provenance,
   timestamps/availability and schema. Reject empty/malformed histories and the existing
   nontrivial all-zero history condition (at least two events), per symbol so another symbol
   cannot mask it. This is a conservative publication quality gate, not a claim that real
   zero funding can never occur. A single properly sourced zero event remains valid. Do not
   infer interval cadence or missing funding from an eight-hour convention.
3. Eliminate last-row-wins in normalizer, client pages and prior/new merge. Identical
   normalized duplicates may collapse deterministically; conflicting values on the same
   (symbol,timestamp_us) key fail closed. API rows must match the requested symbol/window.
   A repeated full funding or instrument page with no progress is an error, not successful
   pagination completion. Validate count/range to avoid zero/negative pagination loops.
4. Publication must not call DatasetPublisher when any requested symbol fetch fails, yields
   unexplained empty results, lacks coverage, has invalid data or conflicts. Include symbols
   skipped because of watermarks in the coverage check: a watermark alone is not coverage.
   Keep discovered/requested universe explicit and unique; no silent shrink. PASS follows
   validated evidence and successful publication, not row count alone. Synthetic fixtures
   are explicitly synthetic; rename misleading real-response test labels. Preserve actual
   supplied rate values, not an assumed fundingRateDaily = 3 * fundingRate relationship.
5. Read prior stage and watermarks before trusting resume. Existing malformed/unreadable
   files fail closed instead of becoming empty state. Validate prior table before conversion.
   A saved watermark needs corresponding validated retained history and cannot be later than
   its maximum event; reject missing stage or ahead/unsupported watermark. Resume inclusively
   at the last known event (with deterministic dedup), not at watermark + eight hours, so
   shorter or changed source intervals are not skipped. Respect explicit requested bounds.
   Overlapping refetch with conflicting evidence stops for review.
6. Keep fetched progress in memory until validated publication succeeds. Never save advanced
   watermarks on fetch/merge/validation/publisher failure. Write the candidate Parquet to a
   separate temporary sibling, validate it, and publish from it through the existing
   DatasetPublisher. Do not overwrite the previous retained stage on prepublication failure.
   After successful catalog registration, atomically promote the candidate to retained stage,
   then atomically replace the watermark file. Order is catalog -> stage -> watermarks;
   crash recovery may refetch data, but must not skip unretained data. Preserve old watermark
   values for unaffected symbols. If a post-publication stage/watermark/report operation fails,
   report failure honestly with the already-published dataset ID; do not claim rollback.
   Use normal same-directory temp-file replacement. No new storage architecture or cross-
   filesystem transaction guarantee is claimed; the existing batch writer is single-writer.
   Retained state is validated every invocation. A damaged legacy state requires explicit
   operator repair rather than silently resetting it in this drop.
7. --dry-run remains fully synthetic and isolated in temporary database/store/watermarks;
   no real network call or production report overwrite. Tests must use tmp_path, including
   the current shared /tmp/39_BITMEX_FULL_BACKFILL.json test. Match the actual synthetic
   discovered full universe (including the historical perpetual) instead of stale count 5.

These corrections enforce existing Gate-0 and retained publication contracts within current
layers; no schema or architecture change is authorized. If the bounded design cannot satisfy
this contract without an architecture decision, stop and report the exact issue.

## Required source tests and one targeted execution

Author meaningful tests for raw field drift/missing/null/nonfinite/bool/wrong types, explicit
normalized round trips, microsecond consistency, unknown availability, per-symbol zero gate,
identical versus conflicting duplicates within/across pages and prior/new merge, wrong-symbol
or out-of-window responses, pagination stall, and malformed retained state. Exercise main's
publication boundary with mock transport and temporary files/catalogs: mixed success/failure,
empty/missing requested symbol, skipped symbol without prior coverage, invalid candidate,
publisher failure and post-publication persistence failure. Prove prior stage/watermark bytes
are unchanged on prepublication failure and that publisher is not called for rejected input.
Prove successful publication precedes stage/watermark advancement, inclusive resume retains
sub-eight-hour events, and synthetic dry-run touches no production paths. No real acquisition.

Under AGENTS.md's targeted senior test exception, Grok may execute exactly once:

```bash
PYTHONPATH=src .venv/bin/python -m pytest tests/ingest/test_bitmex_funding.py tests/ingest/test_bitmex_funding_backfill.py -q --tb=short
```

Run only after the bounded source is ready. Stop on first nonzero result, show exact output;
no post-failure source patch or retry without reviewer disposition. No Ruff, full suite,
acceptance commands, real CLI invocation, integration or evidence publication is assigned.
Report changed paths, SHA-256 hashes/line counts, exact targeted result and limitations.
Then stop for reviewer source inspection. Tests in temporary fixtures do not accept Gate 0.

## Reviewer publication scope

The reviewer may stage/commit/push exactly this review,
`docs/handoff/CURRENT_TASK.md` and `tickets/CEX-002.md` under the governance exception.
CEX-002 and Gate 3 remain IN_PROGRESS; ten products accepted; next ticket NONE.

## Grok model rotation before any source edit

The 4.6 High session read the bounded source and preserved hashes. The reviewer canceled
one discretionary discovery command before execution and explicitly directed continuation
to implementation. The next inference spent several minutes preparing without a source edit
or test execution. The reviewer stopped and closed that route; all five preserved draft
hashes still match and the new test path is absent. This is latency/progress evidence, not
a source rejection or test failure.

Select Grok Build **grok-4.7 High**, the available current Grok model, for the unchanged
six-path contract. This bounded version override of the repository's 4.6 role default uses
the same owner-authorized Grok Build allowance and source-only role. Exactly one Grok actor
is active. No integration exception transfers. The single targeted test remains unexecuted
and authorized once after the source drop is ready. Implement incrementally; do not repeat
the completed discovery or plan. All original scope and stop rules remain.

## Owner correction: continue Grok through completion

The owner rejected the reviewer's premature conclusion that Grok would not produce source.
The reviewer acknowledges interrupting inference too early; elapsed planning time alone did
not establish inability to deliver. The proposed Sol reassignment was not launched.
Grok Build grok-4.7 High remains the sole selected senior and resumes the full six-path
contract through completion, including the one targeted test. The temporary normalization-
only pass restriction is superseded. Do not interrupt merely for planning latency. Normal
approvals, exact scope, test failure stop rule and source-only ownership still apply.

## In-flight source inspection and CLI control correction

Grok produced normalizer, backfill and synthetic-fixture source edits. Reviewer static
feedback requires preserving existing catalog APIs and identity: import the migration
runner from `catalog.runner`, use `PublishPlan.output_specs`, treat
`resolve_latest_by_type` as `str | None`, preserve schema `bitmex_funding` / `1` /
`fund_v1` and transform `bitmex_funding_full_backfill` / `1`, and hash the actual run
configuration. Preserve existing report/helper contracts. Request bounds must retain
microseconds; raw JSON numeric strings are not numeric values. Resolver/close failures
after publication must retain and disclose the already-published dataset ID. These are
corrections inside the existing six-path contract, not added integration authority.

While queuing that feedback, reviewer TUI input was partly consumed by a pending approval
dialog and inadvertently enabled always-approve. The reviewer stopped the inference,
closed the CLI, and resumed the same Grok session with explicit `--permission-mode default`.
The intervening transcript contains a bounded backfill edit and relevant source reads;
no test, Git mutation, integration or real-data execution is recorded. This interruption
restored approval controls, not a latency-based model rotation. The missing feedback was
queued again using bracketed paste. Grok remains the sole selected senior; its first
targeted test is still pending. Source is not accepted by this inspection note.

## First drop disposition and bounded correction — 2026-10-17

The first targeted command ran once and exited 0, with 38 dots at 100%. Repository
pytest configuration already supplies `-q`, explaining the missing summary line when
the authorized command adds another `-q`. Do not rerun solely to obtain that line.
Reviewer independently matched all six reported hashes:

| Path | Lines | SHA-256 |
|---|---:|---|
| `src/cryptofactors/ingest/bitmex_funding.py` | 1049 | `60e836c60fcfa345b08ba305fd1c619ee2dd380a030f3dc81b1f62fdced329aa` |
| `src/cryptofactors/ingest/__init__.py` | 119 | `369be49f416a5dabd0b661511cdd3077bcef12c3a0c8e9481778e09963bc8499` |
| `scripts/research/backfill_bitmex_funding.py` | 987 | `148b8cd0e028a22e96f9dcff5e2ace4f450bf87923e67e218d5355aac9cdd05a` |
| `tests/ingest/test_bitmex_funding.py` | 586 | `7443db617ea4dfb814f1a0fe7d8cec5a17c8cff22d69ff2deeddd3bdc20d9f74` |
| `tests/ingest/test_bitmex_funding_backfill.py` | 476 | `581338a959e39f1115326939715ff96ca39359a721915ebfe44ad891eba24326` |
| `tests/ingest/fixtures/bitmex_funding_source_shapes.json` | 83 | `469f4225d7318687a8af48aa27b1d1c27b16783fdda268009c8fc587fdcc34a3` |

The reviewer rejects the drop for integration pending these specific corrections.
Grok 4.7 High remains the sole source author. Limit changes to the normalizer,
backfill script and their two test files; the fixture and exports now remain frozen.

1. An empty fetch is currently excused whenever the symbol exists anywhere in prior
   history. That is not evidence explaining an empty response, particularly an inclusive
   refetch of a known event. Refuse every attempted empty fetch in this bounded drop.
   A skipped-current symbol must have validated retained observations inside the explicit
   requested window; future-only history plus a later watermark is insufficient. Reject
   missing in-window evidence without publishing or advancing retained state. Do not
   infer complete cadence from this necessary presence check.
2. `_fetch_instrument_page` silently removes non-dictionaries before pagination counts
   are checked, and discovery coerces arbitrary symbols to strings. Fail closed on
   malformed instrument entries and missing/non-string/empty required symbol/type
   fields (and state when a state filter is used). Keep valid non-perpetual instruments
   filterable. Prove a full page containing malformed entries cannot terminate as a
   shorter successful page or silently shrink the discovered universe. For both clients,
   a full page with no progress must fail; a short terminal page of identical duplicate
   observations may collapse successfully, consistent with the duplicate contract.
3. `datetime.fromisoformat` silently truncates fractional precision beyond microseconds.
   Reject source and saved-watermark timestamps whose precision cannot be represented
   exactly by the eight-field microsecond contract. Do not silently round/truncate them.
   Cover sub-microsecond differences that would otherwise collapse into one key.
4. Atomic rename alone does not establish crash-durable ordering. Fsync the candidate
   file before publication, and fsync the retained-stage directory after promotion before
   attempting watermark replacement. Fsync the watermark directory after replacement.
   Preserve catalog -> durable retained stage -> watermarks ordering. An fsync failure
   before publication must not call the publisher or alter old retained bytes; a stage
   barrier failure after publication must disclose the dataset ID and prevent watermark
   advancement. Keep the current single-writer design and existing DatasetPublisher.
5. The mixed-fetch test patches `httpx.Client` twice without restoring the first factory;
   the first empty transport can override the second transport. Its assertion only finds
   the `fetch_errors` dictionary key, which is printed even when its value is empty.
   Use independent cases or restore the original factory. Assert the intended requests
   and actual error, publisher call count zero, and unchanged prior stage/watermark bytes.
   Add missing post-publication watermark/report/close failure cases that verify the real
   published ID, plus the cases above. Tests must exercise behavior rather than merely
   matching an always-present report field.

Keep the already-corrected schema and transform version literals exactly `"1"`.
The rejected `"version1"` replacement never executed. The reviewer corrected the
ambiguous shorthand; the queued old clarification does not authorize another test.
The status poll blocked by approval-review usage limits likewise executed no test.

After these source/test corrections, authorize exactly one new targeted execution:

```bash
PYTHONPATH=src .venv/bin/python -m pytest tests/ingest/test_bitmex_funding.py tests/ingest/test_bitmex_funding_backfill.py -q --tb=short
```

This is a new bounded corrective-drop test, not a retry for display output. Stop on its
first nonzero result, with exact output and no subsequent edit/retry until reviewer
disposition. Report all six hashes/line counts and stop for review. No integration,
acceptance suite, real acquisition, data, record or Git ownership transfers. Gate 0,
Gate 3 and CEX-002 remain open; ten products accepted; next ticket NONE.

### In-flight correction feedback

Reviewer rejected one pending normalizer edit before execution: top-level instrument
helpers were inserted between client methods, which would detach `_get`/`_throttle`
from `BitMEXFundingClient`. Place the helpers outside the complete class body. The
precision helper must also cover every accepted timestamp syntax: checking only the
first dot leaves comma fractions and fractional timezone offsets subject to silent
truncation. Explicit syntax restriction with clear rejection is acceptable. This is
feedback within the four-path contract. Grok received explicit continuation after
the denied edit; the newly authorized targeted test has not run at this point.

The first tested six-path drop is preserved at
`/tmp/cex002_review487_first_tested_drop/`, with an inventory. Static compatibility
inspection also found that the existing MOM-TS dry-run generator omits fundingInterval.
Its synthetic rows will be refused by the strict required-field boundary; no experiment
run or change to that out-of-scope generator is authorized by this source correction.

## Corrected source accepted for Hermes integration — 2026-10-17

The corrective targeted command ran once and exited 0 with 52 dots at 100%. The
reviewer matched all six hashes, inspected the corrective diff and failure assertions,
and accepts these exact bytes for integration. The prior 38-case result is preserved;
the 52-case result applies to the corrected source. The fixture and exports were frozen
through correction. Seven accepted quarantine source hashes and eight unrelated source
hashes still match their preserved inventories.

| Path | Lines | SHA-256 |
|---|---:|---|
| `src/cryptofactors/ingest/bitmex_funding.py` | 1120 | `339c1f27277eb919ba69cbb466f8e84433c53392b09a545983d0b05bc4d3208b` |
| `src/cryptofactors/ingest/__init__.py` | 119 | `369be49f416a5dabd0b661511cdd3077bcef12c3a0c8e9481778e09963bc8499` |
| `scripts/research/backfill_bitmex_funding.py` | 1038 | `3c3883f95b7dc366d0f9540b4193b0788f34be3a9a4993cc293f3deb6112073b` |
| `tests/ingest/test_bitmex_funding.py` | 752 | `2c4d9b74730a6516771dd688a3623feeda205d9c1af57df3a9af8fd0990e316b` |
| `tests/ingest/test_bitmex_funding_backfill.py` | 833 | `1587069bfb7502bbc9ed05bd3f0c32566cc0edb2b6fe64d0240e90656ed45855` |
| `tests/ingest/fixtures/bitmex_funding_source_shapes.json` | 83 | `469f4225d7318687a8af48aa27b1d1c27b16783fdda268009c8fc587fdcc34a3` |

Grok also executed an unassigned syntax/AST command before the corrective pytest:
`py_compile` over the four corrective Python paths, followed by an AST assertion that
`_get`, `_throttle` and `_fetch_instrument_page` remain client methods. It exited 0
and printed `class methods ok True True`. This exceeded the enumerated validation
scope and remains a workflow deviation, not additional acceptance authority. No Git,
real-data execution or evidence publication occurred. The reviewer does not endorse
the extra command. Grok's completed session is closed; source ownership is now frozen.

Select **Jr Dev — Hermes, `meituan/longcat-2.5-preview:free`**, no reasoning override,
for the following execution/integration-only workflow. The public Nous recommended
model endpoint was fetched on 2026-10-17 and lists this exact model at $0.00/1M.
It completed the preceding 225-case quarantine/catalog validation and integration;
its evidence-helper failure remains adverse evidence. This assignment requires no
new helper or data analysis. Step-5's capacity failure and Step-3.7's inference stall
give neither a stronger demonstrated execution route. No fallback providers are
configured. Use interactive CLI with normal approvals; no one-shot/yolo/config changes.

### Ordered integration workflow

1. Read this final section and CURRENT_TASK. Verify HEAD equals origin/main, index
   empty, and the six exact hashes/line counts above. Preserve every unrelated dirty
   and untracked path. No broad discovery, archive/home search, installation or source
   edits. A denied command or first nonzero result stops execution; do not retry.
2. Execute each standalone command in this order:

```bash
PYTHONPATH=src .venv/bin/python -m pytest tests/ingest/test_bitmex_funding.py tests/ingest/test_bitmex_funding_backfill.py -q --tb=short
PYTHONPATH=src .venv/bin/python -m ruff check src/cryptofactors/ingest/bitmex_funding.py src/cryptofactors/ingest/__init__.py scripts/research/backfill_bitmex_funding.py tests/ingest/test_bitmex_funding.py tests/ingest/test_bitmex_funding_backfill.py
python3 scripts/check_repo_control.py
git diff --check -- src/cryptofactors/ingest/bitmex_funding.py src/cryptofactors/ingest/__init__.py scripts/research/backfill_bitmex_funding.py tests/ingest/test_bitmex_funding.py tests/ingest/test_bitmex_funding_backfill.py tests/ingest/fixtures/bitmex_funding_source_shapes.json
```

3. If all pass, stage exactly the six frozen source/test paths, prove the index contains
   only those paths at the accepted hashes, run `git diff --cached --check`, commit
   `CEX-002: integrate strict BitMEX funding publication`, push, and verify HEAD equals
   origin/main. No source/test edits, including lint fixes, are assigned.
4. Whether success or terminal failure, write only
   `research/sprint_004/488_CEX002_BITMEX_NORMALIZER_INTEGRATION_RECORD.md` with exact
   executed commands/results, hashes, integration commit if any, first-stop details,
   and the prior Grok 38/52-case results plus disclosed syntax/AST deviation. Do not
   claim missing commands ran. Update CURRENT_TASK and the current ticket summary/
   actor headers to return control to the reviewer, retaining IN_PROGRESS and next
   ticket NONE. Run repository control and whitespace checks for these three record
   paths, then stage/commit/push exactly the record, CURRENT_TASK and ticket. This
   terminal record publication remains authorized after a validation failure; it does
   not authorize a failed validation retry or source integration.
5. Report commit IDs and stop for reviewer acceptance. No real backfill, quarantine
   rerun, accepted-product audit, production database/store mutation, new data, bundle,
   experiment, model research or next ticket is assigned. Gate 0 is not accepted merely
   by this source inspection; final integration review remains with the reviewer.
