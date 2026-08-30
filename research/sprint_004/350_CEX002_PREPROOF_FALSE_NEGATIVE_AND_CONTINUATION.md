# CEX-002 Preproof False-Negative Correction and Continuation

- **Date:** 2026-08-29
- **Reviewer:** Lead Quantitative Finance Researcher/Engineer
- **Ticket:** CEX-002
- **Decision:** safe preproof stop accepted; false negative corrected; continuation remains authorized
- **Authorized actor:** Jr Dev - Hermes
- **Gate 2:** in progress
- **Next ticket:** `NONE`

## Record-349 disposition

Hermes published record 349 alone in pushed commit
`5ace072da3710ba584748e0419bbbf5ea18c9b3e`. `HEAD == origin/main` at that commit, and the
commit adds exactly
`research/sprint_004/349_CEX002_BOUNDED_ACQUISITION_CONTINUATION.md`. Its SHA-256 is
`2f7a7f5cf84cce320eb2a7b703ee534ce7f8768d1aa4f46e17ce79a28eee227b`.

Hermes correctly stopped before acquisition when its preproof query returned 30,266 terminal
rows rather than the expected 27,658 pending identities. No acquisition command, network
probe, plan, replay, `verify`, repair, state/data mutation, second preproof, or later work ran.
The safe stop and one-path evidence publication are accepted.

The claimed new persisted-state discrepancy is rejected as a query false negative. Review 348
specified exactly 27,658 distinct sidecar-only pending `daily/metrics` revision identities,
not the cumulative number of terminal attempt rows across all runs.

## Independent query-only proof

The reviewer opened only
`file:data/cex002_qualify/gate2/state.sqlite?mode=ro`, immediately set
`PRAGMA query_only=ON`, observed `query_only=1`, and issued aggregate identity/state joins. No
network, acquisition, replay, `verify`, test, source edit, or state/data mutation occurred.

The state is unchanged from Review 348:

```text
receipt_head=ee2740e3f15741d4af5a1fe229851679c5fe9e6d860f38a4a5d14e13cc59c864
plan_entries=737119
attempts=755764
completions=335428
sidecars=363086
terminal_gaps=202
runs=4
publications=4
seals=4
coinalyze_charges=0
charge_transitions=0
unfinished_runs=0
live_available_bytes=221228486656
receipt_post_needed_bytes=184852494246
capacity_state=sufficient
```

The seal-head watermarks remain `attempt_hi=755764`, `completion_hi=335428`,
`sidecar_hi=363086`, `charge_hi=0`, `transition_hi=0`, `run_hi=4`, and `seal_hi=3`.

The apparent discrepancy reconciles exactly:

```text
cumulative terminal attempt rows=30266
distinct terminal identities=27658
prior-run repeated identities=2608
30266 - 2608 = 27658
```

The cumulative row counts reported in record 349 are:

```text
listed byte size does not match=7510 = 656 prior + 6854 current identities
stream exceeded the listed byte ceiling=22755 = 1952 prior + 20803 current identities
streamed digest does not match the required checksum=1
```

Selecting the latest terminal attempt per provider/identity instead produces Review 348's
exact required state:

```text
listed byte size does not match=6854 distinct identities
stream exceeded the listed byte ceiling=20803 distinct identities
streamed digest does not match the required checksum=1 distinct identity
total=27658 distinct identities
with retained sidecar=27658
with completion=0
with terminal gap=0
```

No new run, attempt, sidecar, completion, charge, gap, receipt, publication, seal, or physical
artifact was created after Review 348. No source, authority, storage, or secret-boundary defect
exists. All three Review-348 acquisition invocations remain unused.

## Corrected continuation

Hermes must not rerun the failed cumulative-row query or amend record 349. Before acquisition,
perform only this corrected continuation preproof:

1. prove `HEAD == origin/main` at the Review-350 publication commit, this review is present,
   commit `5ace072` is an ancestor, no path is staged, no `.git/index.lock` exists, and the
   record-349 SHA-256 equals
   `2f7a7f5cf84cce320eb2a7b703ee534ce7f8768d1aa4f46e17ce79a28eee227b`; also prove the
   record-347/acquisition-source/acquisition-test/acquisition-CLI hashes remain the exact
   Review-348 values;
2. prove the governed implementation paths are clean and preserve every unrelated modified or
   untracked path;
3. prove `.env` retains Review 348's ignored/regular/owner/mode/syntax/nonempty-key predicates
   without emitting the key or its length; and
4. open SQLite read-only with `query_only=1`, prove the unchanged receipt/count/capacity/charge
   facts above, and evaluate the revision predicate by latest terminal attempt per
   provider/identity. Require exactly 27,658 distinct identities with the `6,854 / 20,803 / 1`
   message split, 27,658 sidecars, zero completions, and zero gaps.

Any failed corrected predicate stops without acquisition, repair, reset, restore, checkout,
stash, data mutation, or rerun. Do not run a connectivity probe, `plan`, replay, or `verify`.

On corrected preproof success, Review 348's complete acquisition authorization, exact command,
three-message revision envelope, receipt/retry/progress/capacity/Coinalyze/physical-artifact/
secret continuation predicates, and stop rules remain unchanged. Hermes owns up to three
sequential 84,600-second engine invocations inside their 24-hour outer bounds. No invocation
has yet been consumed under that authorization.

For clarity, the exact acquisition command remains:

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

Never rerun an invocation. Exit 3 `complete_with_typed_gaps`, exit 2 `partial`, any new
provider/family/error message, exhausted network failure, failed reconciliation, capacity or
secret failure, low progress, or the third invocation ends the campaign exactly as Review 348
specifies.

## Evidence and Git boundary

Because this correction occupies record 350, after the campaign stops or the third invocation
finishes create exactly:

- `research/sprint_004/351_CEX002_BOUNDED_ACQUISITION_CONTINUATION.md`.

Use Review 348's complete evidence contract. Include the corrected latest-terminal-per-identity
preproof query/summary and do not label cumulative attempt rows as distinct identities.

Use explicit Git-write escalation. Stage only record 351, prove that exact one-path cached set,
commit with message `record CEX-002 bounded acquisition continuation`, push `main`, and stop.
No source/test/governance edit, fourth invocation, replay, `verify`, repair, revision disposal,
Gate 3, normalization, catalog, NautilusTrader, Harmonic Trader, experiment, PAPER/LIVE, or
next-ticket work is authorized. Gate 2 remains `IN_PROGRESS`; next ticket remains `NONE`.

## Reviewer publication scope

The reviewer may stage, commit, and push exactly this review,
`docs/handoff/CURRENT_TASK.md`, and `tickets/CEX-002.md`. Developer evidence, state/data,
`.env`, and unrelated dirty work are excluded.
