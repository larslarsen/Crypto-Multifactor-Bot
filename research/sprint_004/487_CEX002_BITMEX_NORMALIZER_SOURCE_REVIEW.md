# CEX-002 Review 487 — BitMEX normalizer and publication correction

Reviewer: Lead Quantitative Finance Researcher/Engineer
Ticket: CEX-002 (IN_PROGRESS)
Next required actor: Sr Dev — Grok Build (grok-4.7 High)
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
