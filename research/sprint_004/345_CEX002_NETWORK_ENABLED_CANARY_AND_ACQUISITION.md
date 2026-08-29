# CEX-002 network-enabled canary and acquisition

## Authorization and preproof

Review 344 authorized one network-enabled eight-object canary and, only after its exact
predicates passed, one six-hour continuation. Repository/query-only preproof passed at:

```text
HEAD=60ba450bf13080aaf3e2f8242b372a672748226b
ORIGIN_MAIN=60ba450bf13080aaf3e2f8242b372a672748226b
review-344 present=yes
evidence 6c671a0 ancestor=yes
record-343 sha256=8b5d800647a0095fcc599f2c96ee8ded54224eaccd70468c547600f31bc97055
acquisition source sha256=af6ef568b9f0f30827b393efc013b13560d4fd5761ec86417c0d2cf461e1248d
acquisition test sha256=40a75c4e8516f94e9d7528ec036bd7fef964219ac2203768f510364ff30d2624
acquisition CLI sha256=6f4b56ecb43dcc448eb6c8cf765e38d9fa3923432459574d913582e3d9c84043
index/governance clean=yes
.env/key predicates=yes
SQLITE_QUERY_ONLY=1
receipt head=06d9a053d444b073bc6da29edb92006f99eef1ab029cd74270716aaff8872574
plan rows=737119 attempts=27125 completions=73 sidecars=73 gaps=202 charges=0 transitions=0 open_charges=0
```

No separate connectivity probe, plan, replay, or verify was run.

## Canary

The exact authorized canary was run once with explicit external-network escalation:

```text
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

The canary wrapper output was:

```text
command=acquire exit=2 stop=max_objects

TIMING start=2026-08-28T19:23:32.133010474Z end=2026-08-28T19:26:48.682442787Z elapsed_seconds=196.551 exit=2
```

Child stdout and stderr were empty. Query-only reconciliation proved 16 new attempts, all
`class=ok` with HTTP 200; 8 new completions and sidecars; 6,343 new bytes; total 81
completions and sidecars; zero new gaps, errors, charges, transitions, or open charges;
exact plan rejoin; and secret absence. The canary receipt was
`a20aec5a903e4cfee2a61ac888cfdedf5f7d8b3853178fe9fa271a10edf7687c`, with predecessor
`06d9a053d444b073bc6da29edb92006f99eef1ab029cd74270716aaff8872574`.

## Continuation

The exact authorized continuation was then run once with explicit external-network
escalation:

```text
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

The continuation wrapper output was:

```text
command=acquire exit=2 stop=max_wall_seconds

TIMING start=2026-08-28T19:31:11.741846855Z end=2026-08-29T01:24:17.447408294Z elapsed_seconds=21185.704 exit=2
```

Child stdout and stderr were empty. Exit 2 is the accepted bounded stop. No second
acquisition, replay, or verify was run.

## Canonical receipt and reconciliation

The continuation published this canonical receipt:

```text
run_id=de8f39f69840b23420a275fa0085e049437f8174885953cd5af4d42655a2b69b
path=data/cex002_qualify/gate2/run_receipts/207b8f36eece9d7414729e00a7ee206f7ed9841ecb11b50bf41b7ed30d6ff182.json
sha256=207b8f36eece9d7414729e00a7ee206f7ed9841ecb11b50bf41b7ed30d6ff182
predecessor=a20aec5a903e4cfee2a61ac888cfdedf5f7d8b3853178fe9fa271a10edf7687c
prefix_digest=43783bbc72e357d19cf98ae356cecded8ac417e706bddacb3b579435b71d12f2
semantic_state_digest=not separately re-emitted by reconciliation
started_at=2026-08-28T19:33:51.350653+00:00
ended_at=2026-08-29T01:24:03.580668+00:00
stop_reason=max_wall_seconds
```

SQLite was opened read-only as `file:data/cex002_qualify/gate2/state.sqlite?mode=ro` and
immediately set to `PRAGMA query_only=ON`; it reported `SQLITE_QUERY_ONLY=1`.

Exact persisted deltas and totals:

```text
attempt_delta=139038
completion_delta=66910
gap_delta=0
byte_delta=331728893
error_count=2608
plan_entries=737119
attempts=166179
completions=66991
sidecars=69599
terminal_gaps=202
coinalyze_charges=0
charge_transitions=0
open_coinalyze_charges=0
network_calls=139038
```

The run seal and seal head both point to receipt `207b8f36eece9d7414729e00a7ee206f7ed9841ecb11b50bf41b7ed30d6ff182` and predecessor
`a20aec5a903e4cfee2a61ac888cfdedf5f7d8b3853178fe9fa271a10edf7687c`. Seal-head marks are
`attempt_hi=166179`, `completion_hi=66991`, `sidecar_hi=69599`, `charge_hi=0`,
`transition_hi=0`, `run_hi=3`, and `seal_hi=2`.

Continuation attempt facts by class/status were:

```text
ok / 200: 136428
terminal / 200: 2608
transient / 503: 1
transport / NULL: 1
```

The bounded redacted error aggregation was:

```text
AcquisitionError: stream exceeded the listed byte ceiling: 1952
AcquisitionError: listed byte size does not match: 656
ReadError: [Errno 104] Connection reset by peer: 1
```

The 66,910 new completions were all `binance_vision` and added 331,728,893 listed bytes;
the new sidecar count was 69,518. There were no new terminal gaps. No Coinalyze charge,
ledger debit, transition, or open charge was created. The continuation's persisted attempt
facts contained no API-key or authorization field. The filesystem reconciliation found no
retired-tree access.

The receipt's pre-capacity state was sufficient with `available_bytes=244115591168` and
`needed_bytes=188401098252`; post-capacity remained sufficient with
`available_bytes=242324873216` and `needed_bytes=188042954662`. The observed listed-byte
rate was approximately 15.66 KiB/s (`331728893 / 21185.704`); using the frozen projected
new raw total of 20,382,296,129 bytes and treating this rate as a crude bounded estimate,
approximately 20.05 GB remained, or roughly 14.8 days at that observed rate. This is an
estimate, not a completion prediction, and the run's accepted stop is not a full-acquisition
claim.

## Outcome

Review 344's canary and conditional continuation both followed the authorized one-session
boundary. The canary predicates passed, the continuation reached accepted exit 2, and this
record captures the exact wrapper evidence and query-only reconciliation. No source/test
file, plan state, real-data repair, replay, verify, Gate 3 work, or next-ticket work was
performed.
