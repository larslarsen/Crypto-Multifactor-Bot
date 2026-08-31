# CEX-002 bounded acquisition continuation — power-interruption blocker

- **Date:** 2026-08-31
- **Reviewer:** Lead Quantitative Finance Researcher/Engineer
- **Ticket:** CEX-002
- **Authorized actor:** Jr Dev - Hermes
- **Gate 2:** `IN_PROGRESS` / blocked by interrupted invocation
- **Next ticket:** `NONE`

## Disposition

Review 350's corrected latest-terminal-per-identity preproof was satisfied from the
repository and query-only state. One authorized continuation acquisition invocation was
then started. A power interruption stopped the engine before it could publish, seal, or
close its run. This is a new blocker under the Review-350 stop rules. The campaign ends
here. No fourth invocation, replay, `verify`, repair, revision disposal, or later gate ran.

The interruption time and process exit code were not durably captured. No stdout/stderr
log was retained in the store, so no exit code is inferred or invented.

## Corrected preproof

The repository checks were read-only and reported:

```text
HEAD=1b875ac265ba863bcf02e0e6a9058f6eeef4f1a8
ORIGIN_MAIN=1b875ac265ba863bcf02e0e6a9058f6eeef4f1a8
review-350 ancestor=yes
record-349 sha256=2f7a7f5cf84cce320eb2a7b703ee534ce7f8768d1aa4f46e17ce79a28eee227b
record-347 sha256=89dff6c1db36ee04bb29cf13e5968a701b45a70f2c5249536020286991e3b6fe
acquisition source sha256=af6ef568b9f0f30827b393efc013b13560d4fd5761ec86417c0d2cf461e1248d
acquisition test sha256=40a75c4e8516f94e9d7528ec036bd7fef964219ac2203768f510364ff30d2624
acquisition CLI sha256=6f4b56ecb43dcc448eb6c8cf765e38d9fa3923432459574d913582e3d9c84043
staged paths=none
.git/index.lock=absent
.env mode=600 regular=yes owner=lars:lars nonempty-key-syntax=yes
```

The governed CEX-002 implementation paths were clean at preproof. Existing unrelated
modified and untracked paths were preserved.

The read-only SQLite connection used `file:data/cex002_qualify/gate2/state.sqlite?mode=ro`
and immediately set `PRAGMA query_only=ON`; it reported `query_only=1`. The corrected
latest-terminal-per-provider/identity query reported:

```text
latest terminal identities=50921
listed byte size does not match=12576
stream exceeded the listed byte ceiling=38344
streamed digest does not match the required checksum=1
with retained sidecar=50921
with completion=0
with terminal gap=0
```

The preproof state before this invocation was the Review-350 state: receipt head
`ee2740e3f15741d4af5a1fe229851679c5fe9e6d860f38a4a5d14e13cc59c864`, 737119 plan rows,
1307879 attempts, 574392 completions, 625313 sidecars, 202 terminal gaps, five closed
runs, five publications, five seals, zero Coinalyze charges, zero charge transitions,
zero unfinished runs, and sufficient capacity.

## Interrupted invocation

The exact authorized command was:

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

The durable run row is:

```text
run sequence=6
run_id=00fc2af29dbf1e585ecc28974bdb034bdbcf7815b464ea333d5ddc10fae9dab4
started_at=2026-08-31T05:35:00.545590+00:00
ended_at=NULL
stop_reason=NULL
attempt_hi at start=1307879
error_count=50921
network_calls=0 in unfinished metadata (not treated as complete run evidence)
```

Compared with the last sealed high watermarks, query-only state shows:

```text
attempt rows added=235359
  ok / HTTP 200=184434
  terminal / HTTP 200=50921
  transient / HTTP 503=4
completion rows added=92215
sidecar rows added=92219
new listed completion bytes=1459224114
terminal validation messages:
  listed byte size does not match=12576
  stream exceeded the listed byte ceiling=38344
  streamed digest does not match the required checksum=1
terminal gaps added=0
Coinalyze charges=0
charge transitions=0
```

The latest durable totals are 737119 plan rows, 1543238 attempts, 666607 completions,
717532 sidecars, 202 terminal gaps, six run rows, five run publications, five run seals,
zero Coinalyze charges, and zero charge transitions. Run 6 has no publication or seal;
the seal head remains receipt `64099aa5151f12fa09745242b71ecc36ab44e65c7cc5b26f4fddaa64d056a163`
with `attempt_hi=1307879`, `completion_hi=574392`, `sidecar_hi=625313`, `run_hi=5`, and
`seal_hi=4`.

No private partial or terminal artifact was found under the run temporary/terminal roots.
The durable SQLite WAL/SHM files remain present. They are preserved as interrupted-run
state; they were not checkpointed, repaired, deleted, or otherwise mutated by this
handoff. No secret was printed or placed in this record; the persisted attempt facts
were checked for redacted URLs and the charge ledger remains empty.

## Stop and ownership boundary

The power interruption leaves an unfinished acquisition run and prevents the required
receipt/state/physical-artifact reconciliation and sealed continuation predicate. It is
therefore a blocker, regardless of the successful rows already durably recorded. The
unfinished run must not be repaired or accepted as a completed invocation in this ticket.

Only this evidence record is published for the interrupted campaign. Gate 2 remains
`IN_PROGRESS`; no normalization, publication, catalog, consumer check, modeling,
PAPER/LIVE work, or next-ticket work is authorized.
