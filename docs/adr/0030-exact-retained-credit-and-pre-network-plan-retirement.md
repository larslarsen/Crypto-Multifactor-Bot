# ADR 0030 - Exact Retained Credit and Pre-Network Plan Retirement

- **Status:** Accepted
- **Date:** 2026-08-27
- **Amends:** ADR-0029 planning, retained adoption, and code-bound plan replacement
- **Evidence:** `research/sprint_004/258_CEX002_GATE2_STORAGE_SIZING_V3.json`,
  `research/sprint_004/320_CEX002_GATE2_REAL_PLAN_EXECUTION.md`, and
  `research/sprint_004/324_CEX002_RETAINED_AUTHORITY_FAILURE_AND_PLAN_RETIREMENT_ARCHITECTURE.md`

## Context

Receipt 258 is the accepted retained-credit authority. Its
`physical_inputs.retained_credit.keys` field names exactly 73 full Binance object keys,
with key-set SHA-256
`5e13a9fbb57acff21d0c290d3f0da7c27d549031fdee1fca8a1ab0744cc0b982`, 73 unique
objects, 5,225,416 unique bytes, 68 selected-manifest keys, and 5 cost keys. Its lineage
explicitly says that coefficient-only qualification objects supply no retention authority.

The first real plan did not consume that exact set. The planner treated every complete
qualification-progress object which intersected the plan as retained. Ninety such objects
intersected the Binance plan: the 73 receipt-authorized keys plus 17 valid coefficient/sample
objects which are evidence but not retained credit. The installed 737,119-row plan therefore
labels 90 Binance rows as retained while its compact receipt declares 73 retained objects.

The first `acquire` invocation began a run and then correctly failed closed before a network
request or completion when retained adoption independently derived 90 keys and compared that
count with the pinned value 73. The failed store contains one unfinished zero-fact run and no
attempt, completion, sidecar, charge, transition, publication, or seal.

The plan receipt and SQLite authority bind the exact acquisition-source identity. Correcting
the source necessarily changes that identity. Opening the old state under corrected code,
rewriting its authority rows, or silently finalizing its unfinished run would turn a rejected
plan into apparently compatible evidence.

## Decision

### 1. Receipt 258 supplies the only retained-credit set

Planning and acquisition must decode the already hash- and size-pinned receipt 258 and
authenticate its complete retained-credit contract before plan publication:

- schema and ticket;
- a sorted, unique list of non-empty full keys;
- the canonical key-set digest recomputed as SHA-256 of canonical JSON containing
  `{"requirement_keys": sorted_keys}`;
- exact key, unique-object, byte, selected-key, cost-key, and unverified counts;
- equality with the matching lineage key-set digest and count; and
- exact membership in the selected-plus-cost plan and in complete, re-proved qualification
  progress.

The receipt key set, not the intersection of progress and plan, drives both retained plan
fields and `adopt_retained`. A complete progress object outside that set remains qualification
evidence only and is planned as unacquired. No hard-coded replacement list or count-only
acceptance is permitted.

The compact plan receipt must bind the authenticated retained key-set digest. Planning must
reconcile exactly 73 retained labels, 73 unique re-proved objects, 5,225,416 bytes, 68 selected
keys, and 5 cost keys before it installs any state.

### 2. The installed plan is rejected, not migrated in place

Plan identity `911ed811ba5a04008fa787ee88eb4b38a4df3718b169b5c5d914e9ac2f30f578`
and plan receipt
`fb80b372080c7c59a14ecc43d89b1b2438e2b952d2ca571a10f372050f6d3bd3` remain preserved
evidence of the failed first generation. They are no longer an operationally accepted Gate-2
checkpoint. Corrected code must never bind, resume, finalize, or mutate that SQLite state.

After corrected source and tests are accepted, the entire closed
`data/cex002_qualify/gate2` directory must be moved without replacement on device 64513 to:

`data/cex002_qualify/gate2_retired/fb80b372080c7c59a14ecc43d89b1b2438e2b952d2ca571a10f372050f6d3bd3`

The transition must:

1. prove the exact old plan receipt, code identities, 737,119 rows, 90 retained labels, 202
   typed gaps, the one named zero-fact unfinished run, zero acquisition facts, an empty WAL,
   and no live writer;
2. record a complete pre-transition type/device/size/hash inventory without invoking the
   acquisition module;
3. create only the fixed retirement parent, hold the existing acquisition lock, and perform
   one same-device atomic rename with an absent destination and no replacement;
4. durably sync the containing filesystem and prove the old tree at the exact destination,
   the active `gate2` path absent, and every inventoried file unchanged; and
5. stop without cleanup or retry on any failed predicate or transition command.

The retirement is preservation, not deletion and not Gate-2 evidence acceptance. SQLite WAL,
SHM, lock, empty directories, plan receipt, and unfinished run are all moved with the tree.

### 3. Corrected planning starts from an absent active store

Only after retirement succeeds may corrected code execute one network-free `plan` against the
default `data/cex002_qualify` store root. It must create a new `gate2` directory, a new
code-bound plan receipt, and a new SQLite state. The semantic plan identity must differ from
the defective identity because the 17 coefficient-only objects are no longer labeled
retained, while economic scope remains exactly 736,347 Binance objects, 570 Coinalyze logical
receipts, and 202 typed gaps.

The new plan must be reviewed before any acquisition invocation. A source integration,
successful test, retirement, or plan does not authorize a network request, replay, terminal
verification, normalization, or later-gate work.

## Consequences

- Receipt authority, qualification evidence, and plan provenance can no longer be conflated.
- All failed pre-network state is preserved byte-for-byte and cannot be mistaken for the new
  code generation.
- The valid economic universe and free-source requirement are unchanged; only false retained
  provenance is removed.
- Replanning costs SQLite construction time and storage for the retired database, but no raw
  object is discarded or reacquired because the failed run produced none.
- Gate 2 remains `IN_PROGRESS`, and the next ticket remains `NONE`.
