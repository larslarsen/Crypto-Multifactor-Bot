# CEX-002 Power-Interruption Recovery and Continuation

- **Date:** 2026-08-31
- **Reviewer:** Lead Quantitative Finance Researcher/Engineer
- **Ticket:** CEX-002
- **Decision:** safe stop accepted; omitted closed-run evidence corrected; standard interrupted-run recovery authorized
- **Authorized actor:** Jr Dev - Hermes
- **Gate 2:** in progress
- **Next ticket:** `NONE`

## Record-351 and repository disposition

Hermes published record 351 alone in pushed commit
`fbe98b118d08e34e55ae80c0f4121b67417bca4d`. `HEAD == origin/main` at that commit, and
the commit adds exactly
`research/sprint_004/351_CEX002_BOUNDED_ACQUISITION_CONTINUATION.md`. Its SHA-256 is
`84ccb39cc6f1c580278c9a7522a7b469ceb59f658f1f721a8d22935a40068fb0`.

Hermes correctly stopped after the power interruption. Review 350 made any new blocker end
that bounded campaign and prohibited a blind rerun, manual repair, replay, or `verify`.
Record 351 honestly preserves the unfinished run, unknown interruption time, absent process
exit, absent stdout/stderr capture, and durable WAL/SHM state without inventing facts.

Record 351 is incomplete and imprecise in two decision-relevant respects:

1. its block labeled corrected preproof combines the repository/environment preproof with
   state observed after one completed acquisition invocation; and
2. it omits that completed invocation's command outcome, receipt, deltas, retries, revision
   evolution, and physical reconciliation.

The durable chain proves that Review 350 was followed by two acquisition invocations, not one.
Run 5 completed normally and consumed the first invocation. Run 6 began afterward and was
interrupted by the outage, consuming the second invocation and ending the campaign. This
review supplies the missing read-only correction. Do not amend record 351.

Record 351's statement that the unfinished run must not be repaired or accepted as a completed
invocation is accepted only as Hermes's stop boundary. It is not a reviewer prohibition on the
already-accepted ADR-0029 recovery state machine. Standard recovery does not relabel the outage
as success: it finalizes run 6 under its original identity with stop reason `interrupted`, exact
predecessor-owned deltas, and a canonical receipt before a new run can begin.

## Reviewer read-only method

The reviewer performed repository/source inspection, opened only
`file:data/cex002_qualify/gate2/state.sqlite?mode=ro`, immediately set
`PRAGMA query_only=ON`, and observed `query_only=1`. SQLite integrity reported `ok` and the
foreign-key check returned zero defects. Filesystem inspection opened retained content only
read-only with no-follow leaf semantics and compared exact path, regular-file type, size, and
SHA-256 to the durable facts.

No acquisition, network request, replay, `verify`, test, acceptance command, source edit, state
or data mutation, WAL checkpoint, partial cleanup, repair, revision disposal, or retired-tree
access occurred. Existing unrelated modified and untracked paths were preserved.

The accepted implementation identities remain:

- acquisition source:
  `af6ef568b9f0f30827b393efc013b13560d4fd5761ec86417c0d2cf461e1248d`;
- acquisition test:
  `40a75c4e8516f94e9d7528ec036bd7fef964219ac2203768f510364ff30d2624`;
- acquisition CLI:
  `6f4b56ecb43dcc448eb6c8cf765e38d9fa3923432459574d913582e3d9c84043`.

## Omitted run-5 correction

Run 5 is a fully published, sealed invocation whose start snapshot is exactly Review 350's
required four-run state:

```text
run sequence=5
run_id=ee26c916e0e19b1297949c94e3a879f4dbe1cd3b8e8ce3b22f8d2c5f8bcd2f0a
started_at=2026-08-30T05:22:21.627205+00:00
ended_at=2026-08-31T04:53:03.259243+00:00
stop_reason=max_wall_seconds
predecessor=ee2740e3f15741d4af5a1fe229851679c5fe9e6d860f38a4a5d14e13cc59c864
start attempt_hi=755764 completion_hi=335428 sidecar_hi=363086
start charge_hi=0 transition_hi=0 run_hi=4 seal_hi=3 gaps=202
start listed_bytes=3196626487
```

Its canonical 5,526-byte receipt hashes to its content name:

```text
receipt=64099aa5151f12fa09745242b71ecc36ab44e65c7cc5b26f4fddaa64d056a163
attempt_delta=552115
completion_delta=238964
sidecar_delta=262227
gap_delta=0
byte_delta=2430507042
network_calls=552115
error_count=50921
capacity_blocked=false
```

The attempt classification is:

```text
ok / HTTP 200=501191
terminal / HTTP 200=50921
transient / HTTP 503=2
transport / status NULL=1
```

The prior 27,658 latest terminal metrics identities are an exact unchanged subset of run 5's
50,921 terminal identities. Run 5 added 23,263 identities without changing a prior message:

```text
listed byte size does not match=12576
stream exceeded the listed byte ceiling=38344
streamed digest does not match the required checksum=1
```

One transient retry completed. The other transient retry and the one transport retry ended in
the accepted pending metrics ceiling-revision outcome. There is no exhausted network failure,
new family, or fourth message. Every one of the 50,921 identities has a retained sidecar and
zero completion or terminal gap.

Run 5's capacity remained sufficient:

```text
pre available=221237280768 needed=183825436172
post available=204022198272 needed=180382419673
```

Direct physical reconciliation of its exact new sequence ranges proves:

```text
completion rows=238964
unique content paths=238964
content bytes=2430507042
path/type/size/SHA-256 defects=0
sidecar rows=262227
unique sidecar paths=262227
sidecar bytes=25580302
path/type/size/SHA-256 defects=0
```

The run is accepted as bounded Gate-2 progress, not Gate-2 acceptance. The missing presentation
does not justify reacquisition, receipt rewriting, or a Hermes amendment round.

## Interrupted run-6 proof

The current sealed head is the accepted run-5 receipt:

```text
receipt_head=64099aa5151f12fa09745242b71ecc36ab44e65c7cc5b26f4fddaa64d056a163
attempt_hi=1307879
completion_hi=574392
sidecar_hi=625313
charge_hi=0
transition_hi=0
run_hi=5
seal_hi=4
```

Exactly one unfinished run exists:

```text
run sequence=6
run_id=00fc2af29dbf1e585ecc28974bdb034bdbcf7815b464ea333d5ddc10fae9dab4
started_at=2026-08-31T05:35:00.545590+00:00
ended_at=NULL
stop_reason=NULL
start attempt_hi=1307879 completion_hi=574392 sidecar_hi=625313
start charge_hi=0 transition_hi=0 run_hi=5 seal_hi=4 gaps=202
start listed_bytes=5627133529
durable error_count=50921
capacity_blocked=0
run publication rows=0
run seal rows=0
```

The unsealed tail reconciles exactly:

```text
attempt rows=235359
  ok / HTTP 200=184434
  terminal / HTTP 200=50921
  transient / HTTP 503=4
completion rows=92215
sidecar rows=92219
listed completion bytes=1459224114
gap delta=0
charge delta=0
transition delta=0
```

Run 6 retried exactly the same 50,921 terminal identities as run 5: set difference zero in
both directions and zero message changes. All four HTTP-503 identities subsequently completed.
No new provider, family, error message, exhausted network failure, charge, or gap exists.

Direct physical reconciliation proves all 92,215 unsealed content paths and all 92,219
unsealed sidecar paths are unique, regular, content-address correct, exact-size, and SHA-256
matching. The totals are respectively 1,459,224,114 and 8,474,326 bytes, with zero defects.
No private partial or terminal artifact is present. The protected key is nonempty and had zero
byte occurrences in the state database/WAL/SHM, run receipts, or record 351; neither the key nor
its length was emitted.

Current live capacity remains sufficient:

```text
available_bytes=199037587456
stable_requirement_bytes=139577980018
operating_reserve_bytes=39807517492
needed_bytes=179385497510
headroom_bytes=19652089946
```

The current durable totals are 737,119 plan rows, 1,543,238 attempts, 666,607 completions,
717,532 sidecars, 202 gaps, six runs, five publications, five seals, zero Coinalyze charges,
zero charge transitions, and one unfinished run. The current unresolved plan is:

| Provider / family | Complete | Gap | Pending | Pending listed bytes |
|---|---:|---:|---:|---:|
| Binance `daily/bookDepth` | 1 | 0 | 2,234 | 830,372,528 |
| Binance `daily/bookTicker` | 4 | 0 | 905 | 11,687,976,893 |
| Binance `daily/indexPriceKlines` | 12,266 | 0 | 0 | 0 |
| Binance `daily/klines` | 13,710 | 0 | 0 | 0 |
| Binance `daily/markPriceKlines` | 14,096 | 0 | 0 | 0 |
| Binance `daily/metrics` | 522,865 | 0 | 50,921 | 535,441,899 |
| Binance `daily/premiumIndexKlines` | 11,439 | 0 | 0 | 0 |
| Binance `monthly/fundingRate` | 21,035 | 0 | 0 | 0 |
| Binance `monthly/indexPriceKlines` | 21,721 | 0 | 0 | 0 |
| Binance `monthly/klines` | 21,932 | 0 | 0 | 0 |
| Binance `monthly/markPriceKlines` | 22,286 | 0 | 0 | 0 |
| Binance `monthly/premiumIndexKlines` | 5,252 | 0 | 15,680 | 216,791,880 |
| Coinalyze inventory | 0 | 0 | 1 | n/a |
| Coinalyze liquidation | 0 | 0 | 569 | n/a |
| Coinalyze unsupported mapping | 0 | 202 | 0 | n/a |

## Architecture disposition

No ADR or source correction is required. ADR-0029 expressly requires abrupt-kill state to be
recoverable. The accepted source implements the reviewed invariant from Reviews 302 through
307:

1. `bind_session()` authenticates authority, the installed plan, the sealed prefix, and the
   complete receipt chain;
2. `_recover_unfinished_run()` permits exactly one unfinished run and refuses ambiguity;
3. `_finalize_interrupted_run()` retains the original run ID and start snapshot, derives deltas
   from the sealed predecessor to current durable watermarks, uses the durable coordinator-owned
   error/capacity facts, and calls `finish_run()` with stop reason `interrupted`;
4. `finish_run()` atomically persists the exact canonical receipt intent before filesystem
   publication;
5. `complete_publication()` publishes/re-proves the receipt and locator, inserts/re-proves its
   seal, and advances the head by compare-and-swap; and
6. `_require_runnable_head()` prevents a new run until that recovery is fully sealed and no
   unowned fact tail remains.

The accepted test source directly covers process loss after durable attempt/completion progress
and proves the interrupted receipt owns the tail before the resumed run becomes the new head.
This is precisely run 6's state. A manual database edit, stand-alone recovery script, plan,
replay, or `verify` would bypass or duplicate the accepted mechanism and remains prohibited.

## One-invocation recovery and continuation authorization

Hermes owns exactly one standard acquisition invocation. The invocation's network-free binding
phase must first recover and seal run 6 under its original identity; only then may the same
invocation create run 7 and continue the frozen plan. This is a new invocation, not a rerun of
the lost process. It is the only invocation authorized by this review.

Before it, perform one repository/query-only preproof:

1. prove `HEAD == origin/main`, this Review 352 is present, commit `fbe98b1` is an ancestor,
   record 351 has the exact hash above, and the acquisition source/test/CLI have the exact hashes
   above;
2. prove no path is staged, `.git/index.lock` is absent, the three governing implementation
   paths are clean, and every unrelated modified or untracked path is preserved;
3. prove `.env` remains ignored, regular, owned by `lars`, mode `600`, shell-syntax valid, and
   has a nonempty `COINALYZE_API_KEY`, emitting neither the value nor its length;
4. open SQLite read-only with `query_only=1` and prove the exact sealed-head, unfinished-run,
   current-total, unsealed-delta, revision-set, charge, and no-publication/no-seal facts above;
5. prove no `.partial-*` regular file exists under the active tmp, run-receipt, or terminal
   roots, and no terminal artifact exists; and
6. recompute the live ADR-0028 capacity equation and require `sufficient`.

Any failed preproof stops without acquisition, repair, reset, restore, checkout, stash, data
mutation, cleanup, second preproof, or evidence publication. Do not run a connectivity probe,
`plan`, replay, `verify`, or a separate recovery call.

On success, record exact UTC timing and invoke exactly once from the repository root with
explicit external-network escalation:

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

Capture complete bounded stdout/stderr, exit, start/end, and elapsed time. Never rerun it.
After it returns, use only accurately labeled query-only/filesystem/JSON/hash reconciliation.

Recovery is accepted only if the first newly sealed receipt has all of these facts:

```text
run_id=00fc2af29dbf1e585ecc28974bdb034bdbcf7815b464ea333d5ddc10fae9dab4
started_at=2026-08-31T05:35:00.545590+00:00
stop_reason=interrupted
predecessor=64099aa5151f12fa09745242b71ecc36ab44e65c7cc5b26f4fddaa64d056a163
attempt_delta=235359
completion_delta=92215
gap_delta=0
byte_delta=1459224114
network_calls=235359
error_count=50921
attempt_hi=1543238
completion_hi=666607
sidecar_hi=717532
charge_hi=0
transition_hi=0
run_hi=6
seal_hi=5
```

Its post-capacity state must be sufficient, receipt/locator/intent/seal/head transition must be
canonical and exact, and its 50,921 terminal identities and four recovered retries must remain
the exact facts above. The final run-7 receipt must name that recovered receipt as predecessor
and become the final head. A recovery failure, different recovered fact, ambiguous run, orphan
tail, chain failure, or partial publication is a blocker and prohibits another invocation.

For run 7, Review 348's three-message metrics-revision, retry, provider identity/shape,
Coinalyze rate/budget/ledger, capacity, physical-artifact, secret, and receipt predicates remain
in force. Exit 3 `complete_with_typed_gaps`, exit 2 `partial`, or exit 2 `max_wall_seconds` all
end this one-invocation campaign. Any other exit, new provider/family/error message, exhausted
network failure, failed reconciliation, capacity or secret failure also ends it. There is no
second invocation under this review.

## Evidence and Git boundary

After the invocation returns, create exactly:

- `research/sprint_004/353_CEX002_INTERRUPTED_RECOVERY_AND_ACQUISITION_CONTINUATION.md`.

Record the preproof, command and complete bounded output, UTC timing/exit, the recovered run-6
receipt body/hash/locator/intent/seal/head facts, the run-7 receipt and chain transition, exact
per-run and cumulative state/byte deltas, attempt/retry/error classifications, family completion
and remaining totals, revision-set evolution, Coinalyze ledger/outcomes, physical reconciliation,
capacity, secret-absence predicates, stop reason, and proof no later invocation ran. Label all
transformed summaries accurately.

Use explicit Git-write escalation. Stage only record 353, prove that exact one-path cached set,
commit with message `record CEX-002 interrupted recovery continuation`, push `main`, and stop.
Do not amend record 351.

No second acquisition, manual recovery, plan, replay, `verify`, revision disposal, source/test
edit, Gate 3, normalization, catalog, NautilusTrader, Harmonic Trader, experiment, PAPER/LIVE,
or next-ticket work is authorized. Gate 2 remains `IN_PROGRESS`; next ticket remains `NONE`.

## Reviewer publication scope

The reviewer may stage, commit, and push exactly this review,
`docs/handoff/CURRENT_TASK.md`, and `tickets/CEX-002.md`. Developer source/test/evidence paths,
state/data, `.env`, and unrelated dirty work are excluded.
