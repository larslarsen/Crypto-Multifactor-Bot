# CEX-002 Retirement Acceptance and Corrected Plan Authorization

- **Date:** 2026-08-27
- **Reviewer:** Lead Quantitative Finance Researcher/Engineer
- **Ticket:** CEX-002
- **Decision:** rejected-store retirement accepted; one corrected network-free plan authorized
- **Authorized actor:** Jr Dev - Hermes
- **Gate 2:** in progress; acquisition remains unauthorized
- **Next ticket:** `NONE`

## Accepted retirement

The reviewer inspected pushed execution record 337 at SHA-256
`84744cb6e35b9d77c4272278e260c430a83eedebc08ce3d9942b80448f96951d` without
opening either real Gate-2 path. Record 337 is the only path in pushed commit
`8bf45da46abe5ad7770fc283ec92524b1c34a2ca`.

The exact Review-336 command ran once from
`2026-08-28T02:34:22.875764846Z` through `2026-08-28T02:34:30.513845937Z`, elapsed
7.638 seconds, and exited 0. Its bounded canonical receipt proves:

- exact authority SHA-256
  `8c658629a8adcb4eecd46b84509221f83bb053dc916a83f546e4de8e14a4ebc1`;
- rejected plan identity
  `911ed811ba5a04008fa787ee88eb4b38a4df3718b169b5c5d914e9ac2f30f578` and receipt
  `fb80b372080c7c59a14ecc43d89b1b2438e2b952d2ca571a10f372050f6d3bd3`;
- exact source and fixed retired destination paths;
- 10 entries and 742,380,087 regular-file bytes;
- held lock, atomic no-replace rename, parent `fsync`, and filesystem `syncfs`; and
- equal before/after inventory digest
  `5d03cf25826a2e90f2552a98ba9d53539a8fb8bc0aed26d195e102ca41dc83dc`.

The tool also proved the active name absent and the complete destination tree before emitting
success. No second transition, inspection, cleanup, reverse rename, or manual data operation
followed. Review 338 accepts the ADR-0030 retirement as exact preservation of rejected
pre-network state. It does not accept that plan as Gate-2 evidence.

## Corrected plan contract

ADR-0030 now permits one corrected network-free `plan` at the default store root. The accepted
CLI passes `transport=None`; planning has no network path and requires no secret. The operation
must create a fresh active `gate2`, not open or migrate the retired state.

The plan must preserve the full economic scope of 737,119 rows:

- 736,347 `binance_object` rows;
- 1 `coinalyze_inventory` row;
- 569 `coinalyze_liquidation` rows; and
- 202 `coinalyze_unsupported_gap` rows with 202 typed terminal gaps.

The corrected provenance must instead produce:

- schema `cex002_gate2_plan_receipt_v2`;
- policy
  `adr0029_content_addressed_gate2_acquisition_and_resume_adr0030_exact_retained_credit_v2`;
- a semantic plan identity different from the rejected identity above;
- retained key-set SHA-256
  `5e13a9fbb57acff21d0c290d3f0da7c27d549031fdee1fca8a1ab0744cc0b982`;
- exactly 73 retained rows and unique objects, 5,225,416 retained bytes, 68 selected retained
  keys, 5 cost retained keys, and 0 unverified objects;
- the other 736,274 Binance rows explicitly unretained and all 772 Coinalyze rows
  not-applicable to retained credit; and
- zero attempts, completions, sidecars, charges, transitions, runs, publications, seals,
  network calls, or raw payloads.

The new plan receipt and SQLite state require separate reviewer acceptance before any
`acquire` invocation.

## Hermes plan authorization

Hermes owns one plan invocation and execution record 339. Preserve all unrelated modified and
untracked paths.

Repository-only preproof must establish:

- `HEAD == origin/main`, Review 338 is present, and retirement record commit
  `8bf45da46abe5ad7770fc283ec92524b1c34a2ca` is an ancestor of `HEAD`;
- record-337 SHA-256
  `84744cb6e35b9d77c4272278e260c430a83eedebc08ce3d9942b80448f96951d`;
- acquisition source SHA-256
  `af6ef568b9f0f30827b393efc013b13560d4fd5761ec86417c0d2cf461e1248d`, acquisition test
  SHA-256 `40a75c4e8516f94e9d7528ec036bd7fef964219ac2203768f510364ff30d2624`,
  and acquisition CLI SHA-256
  `6f4b56ecb43dcc448eb6c8cf765e38d9fa3923432459574d913582e3d9c84043`;
- no staged path and no `.git/index.lock`; and
- `docs/handoff/CURRENT_TASK.md`, `tickets/CEX-002.md`, ADR-0030, Reviews 324-338, and record
  337 are clean.

Do not open, list, stat, hash, or otherwise inspect the active or retired real Gate-2 paths in
preproof. Record one pre-execution `df -B1 data/cex002_qualify` observation; the plan remains
responsible for its complete live capacity and authority proof. Any failed repository preproof
stops without plan, repair, reset, restore, checkout, stash, staging, or data inspection.

On preproof success, record exact UTC start time and run exactly once from repository root:

```bash
PYTHONDONTWRITEBYTECODE=1 timeout --signal=TERM --kill-after=60s 2h \
  .venv/bin/python scripts/research/acquire_binance_usdm_harmonic_release.py \
  plan --store-root data/cex002_qualify
```

Capture complete stdout/stderr, exact UTC end time, elapsed time, and exit status. Do not retry
or run `plan` a second time for any disposition.

After an actual invocation returns, create exactly:

- `research/sprint_004/339_CEX002_CORRECTED_GATE2_REAL_PLAN_EXECUTION.md`.

For every exit, record the repository commit, exact source/CLI/test identities, exact command,
pre-execution capacity observation, UTC timing, elapsed time, exit status, and complete bounded
stdout/stderr. A nonzero exit or timeout authorizes no data inspection, repair, deletion,
rerun, or later command; publish only the captured execution facts and stop for review.

Only after exit 0, use read-only filesystem, canonical JSON, streaming SHA-256, and Python
standard-library SQLite URI `file:data/cex002_qualify/gate2/state.sqlite?mode=ro`, immediately
followed by `PRAGMA query_only=ON`, to add the following reconciliation to record 339:

- the plan receipt's exact path, bytes, SHA-256, complete canonical JSON, schema, policy,
  plan identity, authority/code/helper identities, family/count/byte facts, storage binding,
  holdout, Coinalyze contract, prohibitions, and exact compact retained-credit block;
- proof that its plan identity differs from the rejected identity and its retained block equals
  the exact 73/5,225,416/68/5/0 contract above;
- `application_id=1127368498`, `user_version=7`, `integrity_check=ok`, no foreign-key
  violation, one authority row, exactly 737,119 plan rows with the four kind counts above,
  exactly 73/736,274/772 retained true/false/not-applicable rows, 202 terminal gaps, and an
  uncharged one-row Coinalyze ledger;
- a seal head naming the new plan receipt, all seven watermarks zero, and a null predecessor;
- zero rows in `attempt`, `sidecar_fact`, `completion`, `coinalyze_charge`,
  `charge_transition`, `run_metadata`, `run_publication`, and `run_seal`; and
- post-plan capacity plus a complete active-tree inventory with type, bytes, device, and
  regular-file hashes, explicitly treating mutable SQLite hashes as evidence rather than
  authority and proving no raw payload, run receipt/link, terminal manifest, or partial file.

Do not invoke the acquisition module or CLI for reconciliation. Record every read-only
inspection command and its exact output. Do not run `verify`; an unacquired plan is expected to
remain incomplete.

Use explicit Git-write escalation. Stage only record 339, prove that exact cached one-path set,
run `git diff --cached --check`, commit with message
`record CEX-002 corrected real Gate-2 plan`, push `main`, and stop for reviewer acceptance. If
record or Git publication fails, do not rerun, repair, or mutate/inspect plan state beyond the
already-authorized reconciliation; return the captured result and publication failure.

No `acquire`, network access, source/test repair, validation rerun, authority refresh, data
deletion, Gate 3, normalization, catalog, NautilusTrader, Harmonic Trader, experiment,
PAPER/LIVE, or next-ticket work is authorized. Gate 2 remains `IN_PROGRESS`; next ticket
remains `NONE`.

## Reviewer publication scope

The reviewer may stage, commit, and push exactly this review,
`docs/handoff/CURRENT_TASK.md`, and `tickets/CEX-002.md`. Developer evidence, state/data, and
unrelated dirty work are excluded.
