# CEX-002 Retained-Authority Failure and Plan-Retirement Architecture

- **Date:** 2026-08-27
- **Reviewer:** Lead Quantitative Finance Researcher/Engineer
- **Ticket:** CEX-002
- **Decision:** acquisition result rejected; defective plan withdrawn; one consolidated senior correction authorized
- **Authorized actor:** Sr Dev - Grok Build, Grok 4.6 High
- **Gate 2:** in progress; no raw acquisition fact exists
- **Next ticket:** `NONE`

## Failed invocation review

Hermes invoked `acquire` exactly once. It exited 5 with:

```text
ERROR: retained credit key count changed
```

Hermes correctly stopped without verification, rerun, repair, evidence publication, Git,
commit, or push. No record 324 was created, so this review occupies that number.

The reviewer inspected the accepted source, receipt 258, qualification progress, installed
plan receipt, filesystem, and SQLite state read-only. The failure is deterministic:

- receipt 258 authorizes exactly 73 retained full keys at key-set SHA-256
  `5e13a9fbb57acff21d0c290d3f0da7c27d549031fdee1fca8a1ab0744cc0b982`,
  73 unique objects, 5,225,416 bytes, 68 selected keys, and 5 cost keys;
- qualification progress has 440 complete objects, of which 90 intersect the installed
  Binance plan;
- the planner calls `_retained_plan_fields` for every progress intersection rather than only
  receipt-authorized keys, so exactly 90 installed Binance rows carry `retained: true`;
- `adopt_retained` independently derives the same 90-key intersection and then compares it to
  the pinned count 73, producing the reported fail-closed authority error; and
- the extra 17 are valid coefficient/sample evidence but receipt 258 explicitly gives them no
  retained-credit authority.

The real store still has 737,119 plan rows, 736,347 Binance rows, 202 typed gaps, and no
attempt, sidecar, completion, charge, charge transition, run publication, or run seal. It has
one unfinished zero-fact run:

- run ID `6528d0ff9ec26b2a9112f607d532ba4ede1126f2be5080e6f18c0a89dae7a406`;
- start `2026-08-27T20:24:52.741721+00:00`;
- zero attempt high-watermark, network calls, deltas, errors, and open charges; and
- no end time or stop reason.

The 742,342,656-byte database was observed at SHA-256
`a6179bf5d015a8b9f9cf4cb654adad90aba5bec6d8d9e645321e4ee8ae7bf6b9`. Its WAL and lock
are empty; the plan receipt remains 4,663 bytes and hashes to its filename
`fb80b372080c7c59a14ecc43d89b1b2438e2b952d2ca571a10f372050f6d3bd3`. Mutable SQLite
and SHM hashes are observations, not durable authority.

Review 324 rejects the acquisition result and withdraws review 321's operational acceptance
of plan identity `911ed811...f578`. The failed result proves that the implementation did not
acquire price-only or any other partial data: it made zero network calls and wrote zero raw
completion facts.

## Architecture decision

ADR-0030 is accepted. Correcting the source changes the code identity bound by the plan
receipt and SQLite authority, so the installed store cannot be resumed or rewritten in place.
It must later be preserved by one atomic same-device retirement, followed by a fresh corrected
plan. That transition and real planning are not authorized in this source round.

## Consolidated senior source authorization

Grok Build may edit exactly:

1. `src/cryptofactors/acquisition/binance_usdm_harmonic_acquisition.py`
2. `tests/acquisition/test_binance_usdm_harmonic_acquisition.py`

The accepted CLI remains unchanged at SHA-256
`6f4b56ecb43dcc448eb6c8cf765e38d9fa3923432459574d913582e3d9c84043`. Preserve all
other source, test, fixture, evidence, ticket, handoff, ADR, configuration, ignored data, and
unrelated dirty paths exactly. Do not use Git and do not run tests or any other command.

### Production correction

Implement the whole authority correction once:

1. Keep receipt 258 hash/size pinning, but decode its bytes instead of discarding them.
2. Authenticate `schema_version == cex002_gate2_storage_sizing_v3`, `ticket == CEX-002`,
   and the complete `physical_inputs.retained_credit` contract. Keys must be non-empty
   strings, strictly sorted, unique full keys. Recompute the sizing canonical key-set digest
   from `{"requirement_keys": sorted_keys}` and require equality with both
   `retained_credit.key_set_sha256` and `lineage.retained_archive_key_set_sha256`.
3. Reconcile exact key, object, unique-byte, selected-key, cost-key, and unverified counts with
   receipt fields, lineage fields, and `AuthorityPins`. Production must prove exactly
   73/73/5,225,416/68/5/0. Do not hard-code the 73 keys or accept a count-only set.
4. Thread the authenticated exact key set through both passes of `iter_plan_objects` and into
   `adopt_retained`. `_retained_plan_fields` must return `retained: false` for every complete
   progress object outside that set without granting it credit.
5. Before plan installation, prove every authorized key is present exactly once in the
   selected-plus-cost universe, has a complete exact progress binding, re-proves its raw and
   sidecar bytes, and reconciles the exact 73 unique objects, 5,225,416 bytes, 68 selected
   keys, and 5 cost keys. Missing, extra, duplicate, outside-plan, unproved, aliased, or
   coefficient-only credit must fail closed.
6. Add the authenticated retained key-set digest and exact decomposition to the compact plan
   receipt without copying the key list. Plan hashing must label only those 73 rows retained.
7. `adopt_retained` must operate only on the authenticated set, re-prove completed retained
   rows as before, preserve storage-neutral hard-link adoption, and never infer authority from
   progress/plan intersection.
8. Preserve every other accepted acquisition, recovery, concurrency, transaction, receipt,
   capacity, provider, secret, and terminal behavior. Do not add migration, force, reset,
   retirement, scope-selection, or compatibility switches.

### Test-source correction

Upgrade the synthetic receipt fixture to contain a real internally consistent retained-credit
and lineage block. Add production-path regressions which:

- construct 90 complete progress objects intersecting the plan while receipt authority names
  exactly 73, prove the plan labels and adopts only 73, prove the other 17 are planned
  unretained and use normal checksum-verified acquisition, and prove no authority-count error;
- prove plan and compact receipt bind the exact key-set digest and the 73/68/5 decomposition;
- reject unsorted, duplicate, missing, extra, outside-plan, incomplete/unproved, wrong-digest,
  wrong-lineage, wrong-key/object/byte, and wrong selected/cost decomposition authority before
  plan publication or the first network call;
- prove changing only the authorized key set changes plan provenance and cannot attach to an
  already installed incompatible plan; and
- preserve the existing process-loss recovery proof for a zero-fact run, while making clear
  that corrected code is never used to finalize the retired real store.

Tests must exercise `run_plan`/`run_acquire` paths rather than only a disconnected helper. Keep
them bounded, synthetic, offline, and outside accepted data.

## Stop boundary

Return once with the two file SHA-256 hashes, line counts, and acquisition test-function count,
plus confirmation that only the two authorized files were edited. Do not run pytest, Ruff,
control, planning, acquisition, verification, qualification, sizing, capacity, network, or
data commands. Do not stage, commit, push, edit governance, or touch the live/retired Gate-2
store.

The reviewer will inspect this complete drop once. Hermes integration, validation, plan-store
retirement, corrected real planning, acquisition, replay, terminal verification, Gate 3,
normalization, catalog, NautilusTrader, Harmonic Trader, experiments, PAPER/LIVE, and
next-ticket work remain unauthorized. Gate 2 remains `IN_PROGRESS`; next ticket remains
`NONE`.

## Reviewer publication scope

The reviewer may stage, commit, and push exactly this review, ADR-0030,
`docs/handoff/CURRENT_TASK.md`, and `tickets/CEX-002.md`. Developer source/test paths, ignored
state/data, execution evidence, and unrelated dirty work are excluded.
