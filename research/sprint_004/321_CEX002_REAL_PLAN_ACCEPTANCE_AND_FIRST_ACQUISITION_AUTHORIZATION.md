# CEX-002 Real Plan Acceptance and First Acquisition Authorization

- **Date:** 2026-08-27
- **Reviewer:** Lead Quantitative Finance Researcher/Engineer
- **Ticket:** CEX-002
- **Decision:** real plan checkpoint accepted; one bounded full-plan acquisition run authorized
- **Authorized actor:** Jr Dev - Hermes
- **Gate 2:** in progress; raw acquisition has not started
- **Next ticket:** `NONE`

## Plan execution review

Hermes ran the review-319 `plan` command once. It exited 0 and printed exactly
`command=plan exit=0 stop=ok`. Hermes published record 320 alone in synchronized commit
`05003b240b4646fe236a3679b762bf2331f6f6b3`.

Record 320 is candid but incomplete against review 319's evidence instructions: its command
wrapper did not retain UTC start/end timestamps or elapsed time, it summarized rather than
recorded the exact read-only inspection commands and output, it omitted post-plan capacity and
the live equation, and it did not state the final shared-tree `git diff --check` result. These
are record defects. They do not justify rerunning the immutable plan or discarding valid state.

The reviewer independently inspected the immutable receipt and opened SQLite with
`mode=ro` plus `PRAGMA query_only=ON`. That direct inspection established:

- plan receipt path
  `data/cex002_qualify/gate2/plan_receipts/fb80b372080c7c59a14ecc43d89b1b2438e2b952d2ca571a10f372050f6d3bd3.json`;
- receipt SHA-256 equal to its filename,
  `fb80b372080c7c59a14ecc43d89b1b2438e2b952d2ca571a10f372050f6d3bd3`,
  with 4,663 bytes and canonical JSON;
- plan identity
  `911ed811ba5a04008fa787ee88eb4b38a4df3718b169b5c5d914e9ac2f30f578`;
- exact accepted authority, Gate-2/helper code, holdout, storage, byte, family, Coinalyze,
  and prohibition facts in the receipt;
- SQLite application ID `1127368498`, user version `7`, integrity `ok`, and no foreign-key
  violation;
- exactly 737,119 plan rows: 736,347 `binance_object`, 1 `coinalyze_inventory`,
  569 `coinalyze_liquidation`, and 202 `coinalyze_unsupported_gap`;
- exactly 202 typed terminal gaps, one authority, one zero-valued Coinalyze ledger, and one
  seal head bound to the plan receipt with all seven high-watermarks zero and no predecessor;
- zero attempts, sidecars, completions, charges, charge transitions, run metadata,
  publications, or run seals; and
- no content payload, run receipt/link, terminal manifest, or temporary partial.

The database was 742,342,656 bytes at evidence SHA-256
`d6a0a18f7bf1c5ccfc62376f0c24257bda640165a27c57aaae9fd2fded5142a4`.
That mutable hash is observation only, never authority. All Gate-2 files were regular or
expected directories on device 64513.

Hermes's pre-plan availability was 246,961,917,952 bytes. Its exact contemporaneous equation
was 139,577,980,018 stable bytes + 49,392,383,591 reserve = 188,970,363,609 required,
leaving 57,991,554,343 bytes of headroom. The reviewer's later read-only post-plan observation
was 245,974,667,264 available bytes. Its equation was 139,577,980,018 + 49,194,933,453 =
188,772,913,471 required, leaving 57,201,753,793 bytes of headroom. Because the filesystem is
shared, the difference between observations is not attributed solely to the plan.

The reviewer accepts the real plan checkpoint when record 320 and this independent review are
read together. Gate 2 is not accepted: no raw acquisition, zero-download replay, or terminal
verification has occurred.

## First acquisition boundary

The complete frozen plan requires 20,351,715,427 projected new Binance raw bytes plus
30,580,702 projected new Coinalyze bytes. The Binance scope is not price-only: it includes the
accepted bar, metrics/open-interest, funding, mark/index/basis inputs, and bounded real
book-ticker/depth cost sample. It excludes trades, aggTrades, and full historical books by
architecture.

`COINALYZE_API_KEY` is currently unset in the execution environment. The first acquisition
run therefore uses both accepted operational bounds:

- `--max-wall-seconds 21000` gives the engine 5 hours 50 minutes to stop scheduling and
  durably settle a run receipt before the six-hour outer process bound; and
- `--max-objects 736274` is the exact 736,347 Binance plan count minus the 73 retained
  Binance objects which `adopt_retained` re-proves and completes before scheduling.

This object bound does not select a family, symbol, date, or price-only subset. It covers every
remaining Binance row in the full immutable order if the wall bound permits, and it prevents
this first run from reaching Coinalyze while the header-only secret is unavailable. A wall stop
earlier than that remains normal resumable progress. Later Coinalyze acquisition still requires
the owner to make a valid free-source key available through the process environment; it must
never be placed in a prompt, command line, repository file, URL, log, receipt, or evidence.

## Hermes execution authorization

Hermes owns one real acquisition invocation and one evidence publication. Preserve every
unrelated modified or untracked path. Do not rerun `plan`.

Preproof must establish without data mutation:

- synchronized `HEAD == origin/main`, with review 321, record-320 commit `05003b2`, and
  review-319 commit `0e3cea2` in ancestry;
- unchanged accepted acquisition source, CLI, test, record-318, plan receipt, and plan
  identities/hashes;
- clean status for all CEX-002 governed repository paths and no staged path;
- the exact accepted read-only state counts and zero-watermark head above;
- all Gate-2 files and authorities on device 64513;
- current capacity sufficient under the live ADR-0028 equation; and
- the `COINALYZE_API_KEY` set/unset state, checked without printing or persisting a value;
  either state is permitted because the exact object bound prevents a Coinalyze attempt.

Record 320 did not establish the required post-publication diff result. Review 321 supersedes
that missing predicate and authorizes one fresh exact `git diff --check` before acquisition.
Retain its complete result for record 322. If it exits nonzero, stop without acquisition or
edit. Do not search an agent transcript and do not run it more than once in this round.

If any other preproof fails, stop without acquisition, repair, deletion, edit, staging, or
rerun and return the exact failed predicate. If it passes, record pre-run `df -B1` capacity and
run exactly once from the repository root:

```bash
PYTHONDONTWRITEBYTECODE=1 timeout --signal=TERM --kill-after=5m 6h \
  .venv/bin/python scripts/research/acquire_binance_usdm_harmonic_release.py \
  acquire --store-root data/cex002_qualify \
  --max-objects 736274 --max-wall-seconds 21000
```

The expected disposition is exit 2, `resumable partial`, with stop reason
`max_wall_seconds` or `max_objects`. That nonzero exit is the designed bounded-session result,
not a command failure. Exit 0 or 3 is not expected before Coinalyze. Exit 4, 5, 6, timeout
status, signal termination, missing run receipt, secret exposure, state/authentication failure,
or any other result stops without repair, deletion, rerun, later command, evidence edit,
commit, or push and returns the exact result for review.

## Expected exit-2 evidence

Only after a normal exit 2 with a fully published run receipt, create exactly:

- `research/sprint_004/322_CEX002_GATE2_FIRST_REAL_ACQUISITION_EXECUTION.md`

Use filesystem/JSON/hash inspection and SQLite `mode=ro` with `PRAGMA query_only=ON`; do not
invoke the acquisition module or CLI for inspection. Record:

- exact command, UTC start/end, elapsed time, exit, stdout/stderr, and stop reason;
- pre/post live capacity equations and available-byte observations;
- run receipt and locator paths, identities, byte lengths, canonical body, predecessor equal
  to the plan receipt, seal/head linkage, and exact high-watermarks;
- exact pre/post/delta plan, attempt, sidecar, completion, gap, charge, transition, run,
  publication, seal, listed-byte, and content-file facts;
- retained adoption count/bytes and exact remaining Binance/Coinalyze counts;
- durable attempt count equal to network-call count, bounded redacted network/error samples,
  retry/outcome counts, and explicit proof that no Coinalyze plan row was attempted;
- no secret value in any URL, database, receipt, log, exception, or evidence;
- content/sidecar physical bytes, deduplicated identities, partial-file absence, and absence of
  terminal artifacts;
- observed completion, network-call, and byte throughput plus a clearly labeled estimate of
  remaining Binance duration derived only from this real run; and
- the review-321 pre-acquisition `git diff --check` command and exact result.

Do not run `acquire` again, `verify`, tests, Ruff, control, qualification, sizing, capacity
attestation, normalization, or any later-gate command. Stage only record 322, prove that exact
cached path set, run `git diff --cached --check`, commit with message
`record CEX-002 first real acquisition execution`, and push `main`. Run the ticket's exact
shared-tree `git diff --check` once after push and report it. Stop for reviewer acceptance with
the pushed commit, record hash/length, receipt identities, reconciliation, throughput/estimate,
clean governed status, and preserved unrelated status.

No second acquisition session, Coinalyze request, source/test repair, authority refresh, data
deletion, terminal verification, Gate 3, normalization, catalog, NautilusTrader, Harmonic
Trader, experiment, PAPER/LIVE, or next-ticket work is authorized. Gate 2 remains
`IN_PROGRESS`; next ticket remains `NONE`.

## Reviewer publication scope

The reviewer may stage, commit, and push exactly this review,
`docs/handoff/CURRENT_TASK.md`, and `tickets/CEX-002.md`. Developer source/test paths, real
acquisition state/data, execution evidence, and unrelated dirty work are excluded.
