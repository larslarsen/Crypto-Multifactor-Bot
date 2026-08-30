# CEX-002 bounded acquisition campaign

## Authorization and preproof

Review 346 authorized up to three sequential bounded network-enabled acquisition sessions,
stopping on the first blocker. The Review-346 repository/query-only preproof passed before
invocation 1:

```text
HEAD=fa9b2990d25089396b155887743d04e7e33b49aa
ORIGIN_MAIN=fa9b2990d25089396b155887743d04e7e33b49aa
review-346 present=yes
evidence 12d6c64 ancestor=yes
record-345 sha256=dea2bf90a1300deccd71865121c996af2a9df911166481c495decf30b28691fa
acquisition source sha256=af6ef568b9f0f30827b393efc013b13560d4fd5761ec86417c0d2cf461e1248d
acquisition test sha256=40a75c4e8516f94e9d7528ec036bd7fef964219ac2203768f510364ff30d2624
acquisition CLI sha256=6f4b56ecb43dcc448eb6c8cf765e38d9fa3923432459574d913582e3d9c84043
index/governance clean=yes
.env/key predicates=yes
head receipt=207b8f36eece9d7414729e00a7ee206f7ed9841ecb11b50bf41b7ed30d6ff182
plan=737119 attempts=166179 completions=66991 sidecars=69599 gaps=202 charges=0 transitions=0 open=0 runs=3 seals=3
PREFLIGHT=PASS
```

No plan, replay, verify, repair, deletion, or separate connectivity probe was run.

## Invocation 1

The first and only campaign invocation was run once from the repository root with explicit
external-network escalation:

```text
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

The complete wrapper output was:

```text
command=acquire exit=2 stop=max_wall_seconds

TIMING start=2026-08-29T02:05:56.745313604Z end=2026-08-30T01:40:27.690909389Z elapsed_seconds=84870.947 exit=2
```

The child stdout and stderr were empty. The accepted exit-2 stop was followed by the required
read-only reconciliation. No second or third invocation was started.

## Canonical receipt and chain

The invocation published and sealed this receipt:

```text
run_id=559908cc3f71a327c92b5410e2f4242c7c920607bc45efd2e7c31f487f306c85
path=data/cex002_qualify/gate2/run_receipts/ee2740e3f15741d4af5a1fe229851679c5fe9e6d860f38a4a5d14e13cc59c864.json
sha256=ee2740e3f15741d4af5a1fe229851679c5fe9e6d860f38a4a5d14e13cc59c864
predecessor=207b8f36eece9d7414729e00a7ee206f7ed9841ecb11b50bf41b7ed30d6ff182
prefix_digest=2e5e2f93425e0020853cc7b55afdf4cd511245cae7c3cb17d205cbee30e308af
semantic_state_digest=e6571eafad082cfbdf06e31a283efdb7683512b0ec5d1c90510a92e86ab6bb06
started_at=2026-08-29T02:09:19.487553+00:00
ended_at=2026-08-30T01:39:49.278793+00:00
stop_reason=max_wall_seconds
```

The run seal and seal head point to the same receipt and predecessor. Seal-head marks are
`attempt_hi=755764`, `completion_hi=335428`, `sidecar_hi=363086`, `charge_hi=0`,
`transition_hi=0`, `run_hi=4`, and `seal_hi=3`.

## Read-only reconciliation

SQLite was opened as `file:data/cex002_qualify/gate2/state.sqlite?mode=ro` and immediately
set to `PRAGMA query_only=ON`; it reported `SQLITE_QUERY_ONLY=1`. The exact persisted run
deltas and cumulative totals were:

```text
attempt_delta=589585
completion_delta=268437
gap_delta=0
byte_delta=2859665835
error_count=27658
network_calls=589585
plan_entries=737119
attempts=755764
completions=335428
sidecars=363086
terminal_gaps=202
coinalyze_charges=0
charge_transitions=0
open_coinalyze_charges=0
unfinished_runs=0
```

The new completions were all `binance_vision`; all 268,437 new completions were in the
remaining Binance archive families. The run added 2,859,665,835 listed bytes and 293,487
new sidecar facts. Capacity remained sufficient: pre-run available/needed bytes were
`241676169216`/`187913213862`, and post-run available/needed bytes were
`226372571136`/`184852494246`. No Coinalyze charge, transition, or open charge occurred.
Persisted attempt facts contained no API-key or authorization field, and captured output
contained no secret.

The observed run rate was approximately 3.16 logical completions/second and 33.8 KiB/s of
listed bytes per second (`268437 / 84870.947` and `2859665835 / 84870.947`). These are
observed rates, not completion guarantees.

## Stop predicate

The progress threshold passed: 268,437 new completions and 2,859,665,835 new bytes exceed
the Review-346 requirement of 10,000 completions or 100,000,000 bytes. Known metrics
revision failures remained the two accepted messages, but a new blocker appeared in the
same invocation:

```text
continuation attempt classes/status:
ok / 200: 561924
terminal / 200: 27658
transient / 503: 2
transport / NULL: 1

terminal errors:
AcquisitionError: stream exceeded the listed byte ceiling: 20803
AcquisitionError: listed byte size does not match: 6854
AcquisitionError: streamed digest does not match the required checksum: 1
```

The first two terminal classes are the known `daily/metrics` frozen-listing revision
messages. The one `streamed digest does not match the required checksum` fact is a new
error family outside Review 346's accepted failure set. It is therefore a campaign blocker;
Review 346 prohibits a second invocation, repair, or disposal of the affected objects.
There were no new typed gaps, and no partial completion claim was made for the mismatching
object.

## Outcome

The campaign stopped after its first invocation on the new checksum-mismatch blocker.
Record 347 contains the preproof, exact invocation timing/output, canonical receipt chain,
read-only state and capacity reconciliation, attempt/error classification, progress, and
stop predicate. No fourth acquisition, second or third campaign invocation, replay, verify,
repair, deletion, Gate 3 work, normalization, catalog work, or next-ticket work was run.
