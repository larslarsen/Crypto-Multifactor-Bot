# CEX-002 DNS Failure Review and Network-Enabled Resume

- **Date:** 2026-08-28
- **Reviewer:** Lead Quantitative Finance Researcher/Engineer
- **Ticket:** CEX-002
- **Decision:** bounded execution accepted as failure evidence; zero downloadable progress
- **Authorized actor:** Jr Dev - Hermes
- **Gate 2:** in progress; network-enabled canary and conditional continuation authorized
- **Next ticket:** `NONE`

## Execution disposition

Hermes invoked the one Review-342 acquisition exactly once and published record 343 alone in
pushed commit `6c671a07228566a17981362491cca61eb287627d`. The command returned accepted
bounded exit 2 after 21,257.042 seconds and published canonical run receipt
`06d9a053d444b073bc6da29edb92006f99eef1ab029cd74270716aaff8872574` with
`max_wall_seconds` stop reason. The receipt is durably linked to corrected plan receipt
`c0b973b2c794804b543225c119eeb8a9fb17798473774859fa92abacca7b9167`.

Review 342's accepted exit classification means the state closed safely; it does not mean raw
acquisition made useful progress. The exact 73 completions and 5,225,416 completion bytes are
the already-authorized retained-credit adoption. There are zero newly downloaded completions,
zero new Binance raw bytes, zero Coinalyze charges, and no Coinalyze request.

Record 343 omits the required attempt classification, remaining-provider/family totals,
throughput estimate, and several exact pre/post/delta facts. The reviewer does not route a
presentation-only amendment. This review supplies the decision-critical correction from a
bounded read-only inspection and accepts record 343 only as the execution and closed-receipt
record when read with this review. Gate 2 remains incomplete.

## Read-only diagnosis

The reviewer opened only
`file:data/cex002_qualify/gate2/state.sqlite?mode=ro`, immediately set
`PRAGMA query_only=ON`, observed `query_only=1`, and issued aggregate and bounded attempt-fact
queries. No acquisition, network request, replay, `verify`, test, source edit, or state/data
mutation was performed.

The persisted facts are exact:

```text
attempts=27125
distinct_attempted_identities=5425
attempts_per_identity=5 for all 5425 identities
class=transport status_code=NULL attempts=27125 identities=5425
error=ConnectError: [Errno -3] Temporary failure in name resolution attempts=27125
new_network_completions=0
```

The arithmetic is decisive: `27,125 = 5,425 * 5`, exactly the source's five-attempt retry
budget. Its `1 + 2 + 4 + 8 + 16 = 31` seconds of backoff per identity across eight workers also
explains the observed session rate. The first and last bounded facts name redacted public
Binance sidecar URLs; no HTTP response was reached. The session was a repository-sandbox DNS
failure, not a slow 20.38 GB transfer and not evidence that the accepted Binance objects are
absent or malformed.

No production-source correction is justified from these facts. The engine preserved every
failure durably, published a resumable receipt, and made no partial completion claim. The next
execution must correct the platform boundary. A sandboxed second run is prohibited.

## Network-enabled canary

Hermes owns one canary invocation and, only after its exact durable success predicates pass,
one long continuation invocation. Both acquisition invocations require explicit platform
escalation for external network access. Approval is authority to reach only the already-pinned
free Binance and Coinalyze sources through the accepted engine; it does not broaden the plan,
permit a purchase, or expose the Coinalyze secret. Do not attempt either acquisition inside the
default network-restricted sandbox.

Preserve every unrelated modified and untracked path. Repository-only preproof must establish:

- `HEAD == origin/main`, Review 344 is present, and evidence commit `6c671a0` is an ancestor;
- record-343 SHA-256
  `8b5d800647a0095fcc599f2c96ee8ded54224eaccd70468c547600f31bc97055`;
- acquisition source SHA-256
  `af6ef568b9f0f30827b393efc013b13560d4fd5761ec86417c0d2cf461e1248d`, test
  SHA-256 `40a75c4e8516f94e9d7528ec036bd7fef964219ac2203768f510364ff30d2624`,
  and CLI SHA-256
  `6f4b56ecb43dcc448eb6c8cf765e38d9fa3923432459574d913582e3d9c84043`;
- no staged path and no `.git/index.lock`; the three governing paths are clean;
- `.env` remains ignored, regular, owned by `lars`, mode `600`, passes `bash -n`, and has a
  nonempty `COINALYZE_API_KEY`, emitting only boolean predicates; and
- query-only state still has receipt `06d9...2574` as its head, exactly 737,119 plan rows,
  27,125 attempts, 73 completions, 73 sidecars, 202 gaps, zero charges/transitions/open
  charges, and no unfinished run.

Any failed preproof stops without acquisition, repair, reset, restore, checkout, stash, data
mutation, or rerun. Do not run a separate `curl`, DNS probe, `plan`, replay, or `verify`.

On preproof success, record exact UTC timing and invoke this canary exactly once from the
repository root with explicit external-network escalation:

```bash
(
  set -a
  . ./.env || exit 5
  set +a
  test -n "${COINALYZE_API_KEY:-}" || exit 5
  export PYTHONDONTWRITEBYTECODE=1
  exec timeout --signal=TERM --kill-after=5m 15m \
    .venv/bin/python scripts/research/acquire_binance_usdm_harmonic_release.py \
    acquire --store-root data/cex002_qualify \
    --max-objects 8 --max-wall-seconds 600
)
```

Capture its complete bounded stdout/stderr, exit, UTC start/end, and elapsed time. Never rerun
the canary. Accepted canary execution requires exit 2 with `max_objects` and a fully published
receipt whose predecessor is `06d9...2574`. Before any continuation, query-only reconciliation
must prove all of these exact predicates:

- `completion_delta=8`, `sidecar` delta 8, total completions/sidecars 81, and positive new raw
  completion bytes;
- `attempt_delta=16`, total attempts 27,141, and every one of the 16 new attempt facts is
  class `ok` with HTTP status 200;
- run `error_count=0`, zero new gaps, zero charges/transitions/open charges, and no partial or
  terminal artifact; and
- the eight new completions rejoin their exact plan identities, content addresses, listed
  byte sizes, sidecars, and provider checksums without a secret-bearing persisted field.

Any command or predicate failure rejects the canary, prohibits the continuation, and proceeds
only to record 345 publication with the captured and read-only facts. Do not repair or rerun.

## Conditional long continuation

Only if every canary predicate above passes, immediately record fresh UTC timing and invoke
this continuation exactly once, again with explicit external-network escalation:

```bash
(
  set -a
  . ./.env || exit 5
  set +a
  test -n "${COINALYZE_API_KEY:-}" || exit 5
  export PYTHONDONTWRITEBYTECODE=1
  exec timeout --signal=TERM --kill-after=5m 6h \
    .venv/bin/python scripts/research/acquire_binance_usdm_harmonic_release.py \
    acquire --store-root data/cex002_qualify --max-wall-seconds 21000
)
```

Accepted command exits remain 2 `max_wall_seconds` or 3 `complete_with_typed_gaps`. Any other
exit stops without repair or rerun. For exit 2, useful progress requires at least one new
completion beyond the accepted canary; exit classification alone is not an acquisition-success
claim. The reviewer will decide the resulting state from the exact evidence.

## Record and integration boundary

After the canary, create exactly:

- `research/sprint_004/345_CEX002_NETWORK_ENABLED_CANARY_AND_ACQUISITION.md`.

If the canary rejects, record only its command/timing/output, receipt and state deltas, exact
attempt-class/error aggregation, failed predicate, proof that no continuation ran, and secret-
absence predicates. If it accepts, record those canary facts plus the long continuation's
exact command/timing/output and the complete Review-342 accepted-exit reconciliation contract:
receipt body/hash/chain/watermarks, exact pre/post/delta counters and bytes, attempt classes and
bounded redacted samples, provider/family completion and remaining totals, partial/terminal
artifact absence, Coinalyze shape/rate/ledger/outcomes, secret-absence predicates, capacity,
observed throughput, and an honestly derived remaining-duration estimate. Label transformed
summaries accurately; do not call them verbatim or raw.

Use explicit Git-write escalation. Stage only record 345, prove that exact one-path cached set,
commit with message `record CEX-002 network-enabled acquisition`, push `main`, and stop for
review. Do not modify record 343. No source/test/governance edit, second canary, further
acquisition, replay, `verify`, repair, deletion, Gate 3, normalization, catalog,
NautilusTrader, Harmonic Trader, experiment, PAPER/LIVE, or next-ticket work is authorized.

## Reviewer publication scope

The reviewer may stage, commit, and push exactly this review,
`docs/handoff/CURRENT_TASK.md`, and `tickets/CEX-002.md`. Developer evidence, state/data,
`.env`, and unrelated dirty work are excluded.
