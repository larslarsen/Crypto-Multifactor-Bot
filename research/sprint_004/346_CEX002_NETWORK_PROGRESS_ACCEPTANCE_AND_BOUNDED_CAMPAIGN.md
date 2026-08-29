# CEX-002 Network Progress Acceptance and Bounded Campaign

- **Date:** 2026-08-28
- **Reviewer:** Lead Quantitative Finance Researcher/Engineer
- **Ticket:** CEX-002
- **Decision:** canary and real progress accepted; bounded continuation campaign authorized
- **Authorized actor:** Jr Dev - Hermes
- **Gate 2:** in progress
- **Next ticket:** `NONE`

## Record disposition

Hermes published record 345 alone in pushed commit
`12d6c64ebf7e1bba65da7edf23645c3c9ea30021`. Its SHA-256 is
`dea2bf90a1300deccd71865121c996af2a9df911166481c495decf30b28691fa`.
The Review-344 canary passed every exact predicate: exit 2 `max_objects`, 16 new class-`ok`
HTTP-200 attempts, eight new Binance completions and sidecars, zero errors, and a canonical
receipt linked to the DNS-failure receipt. The externally network-enabled boundary is accepted.

The conditional continuation then ran once and closed with accepted exit 2
`max_wall_seconds`. It added 66,910 checksum-verified Binance completions and 331,728,893
listed bytes under canonical receipt
`207b8f36eece9d7414729e00a7ee206f7ed9841ecb11b50bf41b7ed30d6ff182`.
Current durable totals are 66,991 completions, 69,599 sidecars, 166,179 attempts, 202 typed
unsupported gaps, and zero Coinalyze charges or transitions. Capacity remained sufficient.

Record 345 says the receipt semantic digest was not separately re-emitted. The canonical
receipt itself records
`e20665ec08981a3dc23415dbabd221637b5770a885a4c5aad4bb22ffc135c7c3`.
This review supplies that bounded correction; no presentation-only amendment is authorized.

## Revision failures

The continuation also persisted 2,608 terminal HTTP-200 validation failures. Reviewer
query-only inspection proves every one is in `daily/metrics` and has exactly one of these
messages:

```text
stream exceeded the listed byte ceiling: 1952
listed byte size does not match: 656
```

The affected frozen intervals are confined to `2024-04-04` through `2024-04-30` and
`2026-03-27` through `2026-06-10`, with 27,379,397 frozen listed bytes. Their current checksum
sidecars are retained, but no mismatching raw response was published and no completion was
claimed. Other attempted families completed cleanly. One transient HTTP 503 and one connection
reset recovered inside the bounded retry policy and did not become worker errors.

These facts are consistent with official archive metrics objects being revised after the
listing snapshot was frozen. They are not permission to overwrite plan facts, ignore the
objects, or call them gaps. ADR-0029 correctly leaves them pending for later reviewer
disposition. Repeating them once per resumed process is bounded overhead; rewriting the
code-bound state before acquiring the remaining unaffected requirement would add greater risk
and delay. Source-authority amendment work is deferred until the engine reaches the end of the
current plan or a campaign stop predicate establishes a new blocker.

Record 345's 14.8-day byte-rate estimate is arithmetically labeled but not decision-useful.
This segment was dominated by small per-request objects, while 11.69 GB of the remaining bytes
are concentrated in only 905 `daily/bookTicker` objects. The observed logical completion rate
was about 3.16 objects/second. At that rate the 669,926 currently pending downloadable logical
entries represent roughly 59 hours of network execution, before family-size and retry effects.
This is the basis for the bounded campaign, not a completion promise.

## Campaign authorization

Hermes owns up to three sequential acquisition invocations. Each has an 84,600-second engine
wall bound inside a 24-hour outer bound. This permits up to 70.5 engine hours, enough to cover
the current request-rate estimate without an intervening presentation review. The invocations
remain individually bounded and resumable; this is not authority for an unbounded daemon.

Preserve every unrelated modified and untracked path. Before the first invocation only,
repository/query-only preproof must establish:

- `HEAD == origin/main`, Review 346 is present, and commit `12d6c64` is an ancestor;
- record-345, acquisition source, acquisition test, and CLI SHA-256 values equal respectively
  `dea2bf90a1300deccd71865121c996af2a9df911166481c495decf30b28691fa`,
  `af6ef568b9f0f30827b393efc013b13560d4fd5761ec86417c0d2cf461e1248d`,
  `40a75c4e8516f94e9d7528ec036bd7fef964219ac2203768f510364ff30d2624`, and
  `6f4b56ecb43dcc448eb6c8cf765e38d9fa3923432459574d913582e3d9c84043`;
- no staged path or `.git/index.lock`; the three governing paths are clean;
- `.env` retains the accepted ignored/regular/owner/mode/syntax/nonempty-key predicates without
  emitting the key or its length; and
- query-only state has receipt `207b...f182` as its head, the exact totals above, 2,608
  sidecar-only pending `daily/metrics` identities, no unfinished run, no open charge, and
  sufficient capacity.

Any failed preproof stops without acquisition, repair, reset, restore, checkout, stash, data
mutation, or rerun. Do not run a separate connectivity probe, `plan`, replay, or `verify`.

For each authorized invocation, record exact UTC timing and invoke exactly once from the
repository root with explicit external-network escalation:

```bash
(
  set -a
  . ./.env || exit 5
  set +a
  test -n "${COINALYZE_API_KEY:-}" || exit 5
  export PYTHONDONTWRITEBYTECODE=1
  exec timeout --signal=TERM --kill-after=5m 24h \
    .venv/bin/python scripts/research/acquire_binance_usdm_harmonic_release.py \
    acquire --store-root data/cex002_qualify --max-wall-seconds 84600
)
```

Capture complete bounded stdout/stderr, exit, start/end, and elapsed time. Never rerun an
invocation. After each invocation, use only accurately labeled query-only/filesystem/JSON/hash
reconciliation. Another invocation is authorized only when all continuation predicates pass:

- the new canonical receipt is fully published and linked to the prior head;
- exit 2 has stop reason `max_wall_seconds`; exit 3 `complete_with_typed_gaps` instead ends the
  campaign successfully and prohibits another invocation;
- every terminal HTTP-200 validation failure is a `daily/metrics` size mismatch with one of the
  two exact messages above, and each such identity remains pending with a sidecar and without a
  completion;
- every exhausted worker error is accounted for by those terminal metrics-size identities;
  transient/rate-limit/transport retries may occur only when the identity later completes in
  that invocation;
- there is at least one new completion and, for `max_wall_seconds`, either at least 10,000 new
  completions or at least 100,000,000 new completion bytes;
- capacity remains sufficient, the receipt/state/high-watermark/physical-content deltas
  reconcile, no partial/terminal artifact remains, and no open Coinalyze charge exists; and
- the secret is absent from captured output and all persisted URL/query/database/receipt/
  evidence fields without printing the secret or its length.

Exit 2 with stop reason `partial` means the scheduler reached the end with unresolved entries.
It ends the campaign and prohibits another invocation, even if all other predicates pass. Any
unaccepted exit, new error family/message, exhausted network failure, failed reconciliation,
capacity block, secret predicate failure, or low-progress result also ends the campaign without
repair or rerun. Do not delete or modify the 2,608 known revision facts between sessions.

## Evidence publication

After the campaign stops or the third invocation finishes, create exactly:

- `research/sprint_004/347_CEX002_BOUNDED_ACQUISITION_CAMPAIGN.md`.

Record the preproof, every invoked command and complete bounded output, UTC timings, exits,
receipt bodies/hashes/chain/watermarks, exact per-run and cumulative state/byte deltas,
attempt/error classifications and bounded redacted samples, provider/family completed and
remaining totals, the exact revision-failure set evolution, Coinalyze ledger/outcomes, physical
artifact reconciliation, capacity, secret-absence predicates, observed object/byte rates, stop
predicate, and proof that no unauthorized later invocation ran. Label transformed summaries
accurately.

Use explicit Git-write escalation. Stage only record 347, prove the exact one-path cached set,
commit with message `record CEX-002 bounded acquisition campaign`, push `main`, and stop for
review. No source/test/governance edit, fourth acquisition, replay, `verify`, repair, deletion,
Gate 3, normalization, catalog, NautilusTrader, Harmonic Trader, experiment, PAPER/LIVE, or
next-ticket work is authorized. Gate 2 remains `IN_PROGRESS`; next ticket remains `NONE`.

## Reviewer publication scope

The reviewer may stage, commit, and push exactly this review,
`docs/handoff/CURRENT_TASK.md`, and `tickets/CEX-002.md`. Developer evidence, state/data,
`.env`, and unrelated dirty work are excluded.
