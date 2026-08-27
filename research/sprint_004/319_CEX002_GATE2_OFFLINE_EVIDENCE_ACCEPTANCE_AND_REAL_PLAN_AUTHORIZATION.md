# CEX-002 Gate-2 Offline Evidence Acceptance and Real Plan Authorization

- **Date:** 2026-08-27
- **Reviewer:** Lead Quantitative Finance Researcher/Engineer
- **Ticket:** CEX-002
- **Decision:** corrected offline evidence accepted; one real network-free plan authorized
- **Authorized actor:** Jr Dev - Hermes
- **Gate 2:** in progress; acquisition has not started
- **Next ticket:** `NONE`

## Accepted checkpoint

Accept record 318 and pushed commit
`4acbdbe72900cf98880b67d276bc1ac9ec7ee8a8` as the corrected Gate-2 offline
validation checkpoint. The accepted Gate-2 identities are:

- acquisition source:
  `0f8bbf70db167420b5fd5e3b3d0e4d5ed441de580c886909c7bd55426a233981`;
- CLI: `6f4b56ecb43dcc448eb6c8cf765e38d9fa3923432459574d913582e3d9c84043`;
- 177-test source:
  `6157fd1f6ba0feccb83965a0ac383985577763edcedc92b0980a4c4cbd499ad6`;
  and
- corrected evidence record 318:
  `47425810c0066159e5d030afb211fa27b2d67586ed1ccde74b3029bcdc5dbb79`.

Focused Gate-2 Ruff and all 177 targeted tests passed. Clean same-device repository-wide
Ruff and repository control passed. The exact final shared-tree `git diff --check` exited
0 with no output. Ticket-wide pytest remains formally non-passing because of the five
accepted unrelated baseline failures identified in reviews 315 and 318. Those failures do
not implicate Gate 2 and are not authorized for repair under CEX-002.

## Architectural boundary

The next real operation is the immutable Gate-2 `plan`, not a partial acquisition and not
an experiment. The accepted CLI passes `transport=None` to `run_plan`; `run_plan` rejects
any non-`None` transport before work. Planning therefore has no network path and requires
no Coinalyze secret.

The operation reauthenticates the frozen qualification report, compressed and uncompressed
manifest identities, cost selection, receipt 258, renewable capacity attestation 282,
listing and contract authorities, holdout, helper code, and accepted Gate-2 code. It then:

1. streams and derives the complete plan and its identity without materializing the full
   manifest;
2. publishes one immutable content-named canonical plan receipt;
3. installs the full plan, typed unsupported gaps, zero charge ledger, and zero-watermark
   receipt-chain head in one `BEGIN IMMEDIATE` SQLite transaction; and
4. closes without an acquisition attempt, network call, raw download, run receipt, or
   terminal publication.

An injected post-flush failure is covered by the accepted rollback test. Because the plan
receipt is published before the SQLite transaction, a failed operation may leave that
immutable receipt even when the database transaction rolls back. Such a failure is a
review boundary, not authority to delete state or rerun.

The exact production plan must contain 737,119 rows:

- 736,347 `binance_object` rows;
- 1 `coinalyze_inventory` row;
- 569 `coinalyze_liquidation` rows; and
- 202 `coinalyze_unsupported_gap` rows, each represented by one typed terminal gap.

This is the full harmonic-ready raw acquisition plan. Its receipt expressly prohibits
trades/aggTrades, full historical books, price-only/tick paths, and caller-selected
family/symbol/date subsets.

## Capacity observation

Immediately before this review publication, the accepted destination was still absent at
`data/cex002_qualify/gate2`, and the store and every checked authority were on device
64513. A read-only `df -B1` observation reported 247,016,914,944 available bytes. Under
ADR-0028 that observation implies:

- stable future requirement: 139,577,980,018 bytes;
- renewable operating reserve: 49,403,382,989 bytes;
- total required at that instant: 188,981,363,007 bytes; and
- observed headroom: 58,035,551,937 bytes.

These are approximately 139.6 GB stable requirement, 49.4 GB reserve, and 58.0 GB
headroom in decimal units. They are a reviewer observation, not the execution proof. The
real plan must recompute current availability and fail closed if the live capacity equation
does not pass. The plan itself writes plan metadata; the stable requirement reserves the
later complete acquisition, normalization/catalog, temporary high-water, and operating
space defined by the accepted sizing authority.

## Hermes real-plan authorization

Hermes owns one real plan execution and its evidence publication. Work from the repository
root. Preserve every unrelated modified or untracked path.

Preproof must establish all of the following without mutation:

- synchronized `HEAD == origin/main`, with this review and commit `4acbdbe7` in its
  ancestry;
- the four exact accepted hashes above;
- clean status for the acquisition source, CLI, test source, and record 318;
- no staged path;
- `data/cex002_qualify/gate2` is absent; and
- the repository, accepted store, report 62, receipt 258, attestation 282, qualification
  authorities/caches, retained raw store, and holdout are present on device 64513.

If any preproof fails, stop without plan, edit, staging, or repair and return the exact
failed predicate. If it passes, record pre-execution `df -B1` availability and run exactly
once:

```bash
PYTHONDONTWRITEBYTECODE=1 timeout --signal=TERM --kill-after=60s 2h \
  .venv/bin/python scripts/research/acquire_binance_usdm_harmonic_release.py \
  plan --store-root data/cex002_qualify
```

Record UTC start/end timestamps, elapsed time, exit code, and complete stdout/stderr. If
the command exits nonzero, receives a timeout/signal, or does not close normally, stop
without repair, deletion, rerun, inspection that could mutate state, evidence edit,
staging, commit, or push. Return the exact result and the resulting Gate-2 path inventory
for reviewer disposition.

## Success evidence and publication

Only after exit 0, use read-only filesystem, JSON, hashing, and SQLite inspection to create
exactly:

- `research/sprint_004/320_CEX002_GATE2_REAL_PLAN_EXECUTION.md`

Do not invoke the acquisition module or CLI for inspection because opening its state class
is a write-capable operation. Open SQLite read-only with Python's standard-library
`sqlite3` URI `file:data/cex002_qualify/gate2/state.sqlite?mode=ro` and immediately set
`PRAGMA query_only=ON`. The evidence must record:

- pre/post available bytes and the exact live capacity equation;
- the plan receipt path, SHA-256, byte length, canonical JSON body, plan identity,
  authority/code/helper identities, counts, byte facts, family totals, Coinalyze contract,
  holdout, storage binding, and prohibitions;
- `PRAGMA application_id == 1127368498`, `user_version == 7`,
  `integrity_check == ok`, and no foreign-key violation;
- exactly 1 authority row, 737,119 plan rows with the four exact kind counts above,
  202 terminal gaps, 1 charge-ledger row with `charged == 0`, and 1 seal-head row;
- zero rows in `attempt`, `sidecar_fact`, `completion`, `coinalyze_charge`,
  `charge_transition`, `run_metadata`, `run_publication`, and `run_seal`;
- seal head `receipt_sha256` equal to the plan receipt, all seven high-watermarks equal
  to zero, and `predecessor_sha256 IS NULL`;
- the Gate-2 file inventory with type, bytes, device, and hashes for regular files,
  explicitly marking the mutable SQLite hash as evidence rather than authority; and
- no content payload, run receipt/link, terminal manifest, or temporary partial file.

Record every inspection command and its exact output. Do not run `plan` again to prove
idempotence. Do not run `verify`: an incomplete acquisition is expected to remain pending.

Stage only record 320. Prove that exact cached path set and run
`git diff --cached --check`. Commit with message `record CEX-002 real Gate-2 plan execution`
and push `main`. Then run the ticket's exact shared-tree `git diff --check` once and report
its exit code and output. Stop for reviewer acceptance with the pushed commit, record hash
and length, exact plan result, plan receipt identity, read-only reconciliation, clean
Gate-2 source/governance status, and preserved unrelated status.

No `acquire`, `verify`, network access, source/test repair, validation rerun, authority
refresh, data deletion, Gate 3, normalization, catalog, NautilusTrader, Harmonic Trader,
experiment, PAPER/LIVE, or next-ticket work is authorized. Gate 2 remains `IN_PROGRESS` and
the next ticket remains `NONE`.

## Reviewer publication scope

The reviewer may stage, commit, and push exactly this review,
`docs/handoff/CURRENT_TASK.md`, and `tickets/CEX-002.md`. Developer source/test paths,
real plan state/data, execution evidence, and unrelated dirty work are excluded.
