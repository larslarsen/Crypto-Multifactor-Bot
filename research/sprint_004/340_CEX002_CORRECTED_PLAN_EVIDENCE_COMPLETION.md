# CEX-002 Corrected Plan Evidence Completion

- **Date:** 2026-08-27
- **Reviewer:** Lead Quantitative Finance Researcher/Engineer
- **Ticket:** CEX-002
- **Decision:** corrected plan semantics pass; execution record incomplete
- **Authorized actor:** Jr Dev - Hermes
- **Gate 2:** in progress; acquisition remains unauthorized
- **Next ticket:** `NONE`

## Plan disposition

Hermes executed Review 338's corrected network-free plan once in 171.325 seconds with exit 0
and published record 339 alone in pushed commit
`fe0ad88afc80271e6ca86bb8e9d91722c2c263ae`. The installed plan must not be deleted,
repaired, or rerun.

Record 339 proves the decision-critical corrected semantics:

- receipt SHA-256
  `c0b973b2c794804b543225c119eeb8a9fb17798473774859fa92abacca7b9167`, schema v2,
  and explicit ADR-0029/ADR-0030 v2 policy;
- new plan identity
  `8d96db46d5b6df45e4b9c0ba0e45ae9f3688dd88503195fb426e12de827bde22`, distinct
  from the rejected identity;
- 737,119 rows with exact 736,347/1/569/202 kind distribution and 202 terminal gaps;
- exact retained-credit digest and 73 objects, 5,225,416 bytes, 68 selected keys, 5 cost keys,
  0 unverified objects, and SQLite retained split 73 true/736,274 false/772 not-applicable;
- application/user versions, integrity, foreign keys, zero-fact tables, uncharged ledger, and
  zero-watermark plan-receipt seal head; and
- pre/post available capacity of 249,268,436,992 and 248,392,949,760 bytes.

The corrected plan semantics pass. Acquisition remains withheld because record 339 does not
satisfy Review 338's evidence-publication contract.

## Evidence gaps

Record 339 says the complete canonical receipt was read verbatim but publishes only selected
facts. It omits:

1. the complete canonical receipt JSON;
2. its exact authority, code identity, helper identities, family totals, storage, holdout,
   Coinalyze, and prohibitions blocks;
3. the exact commands used for the read-only JSON, SQLite, capacity, and inventory
   reconciliation and their complete bounded outputs; and
4. the complete active-tree inventory with every relative path, type, device, mode, byte size,
   and regular-file SHA-256. The prose size list is not that inventory.

These are evidence defects only. They do not authorize source repair, plan rerun, or a second
semantic plan.

## Hermes evidence correction

Hermes must edit only:

- `research/sprint_004/339_CEX002_CORRECTED_GATE2_REAL_PLAN_EXECUTION.md`.

First use the already-captured Review-338 transcript/output wherever complete. If any exact
required value was not retained, perform only the minimum read-only reconciliation needed to
recover it:

- read and stream-hash the one content-named plan receipt and publish its complete canonical
  JSON verbatim;
- open SQLite only with Python standard-library URI
  `file:data/cex002_qualify/gate2/state.sqlite?mode=ro`, immediately set
  `PRAGMA query_only=ON`, and query only the already-authorized Review-338 facts; and
- list/lstat the active tree without following links and stream-hash regular files.

Do not invoke the acquisition module or any repository CLI. Do not write, create, rename,
delete, chmod, repair, checkpoint, reconcile WAL, rerun `plan`, invoke `verify`/`acquire`, or
access the retired tree. Do not repeat facts already complete merely to produce a different
presentation.

Amend record 339 with all four missing evidence groups above. Preserve its exact execution
timing/output and existing correct facts. Explicitly identify the mutable SQLite hash as
post-plan evidence rather than authority. Keep secrets absent and output bounded.

Use explicit Git-write escalation. Stage only record 339, prove that exact cached one-path set,
run `git diff --cached --check`, commit with message
`complete CEX-002 corrected plan evidence`, push `main`, and stop for review. Return the record
SHA-256, line count, correction commit, and whether any read-only reinspection was necessary.

No source/test/governance edit, Ruff, pytest, control, planning, acquisition, network access,
later gate, normalization, catalog, NautilusTrader, Harmonic Trader, experiment, PAPER/LIVE, or
next-ticket work is authorized. Gate 2 remains `IN_PROGRESS`; next ticket remains `NONE`.

## Reviewer publication scope

The reviewer may stage, commit, and push exactly this review,
`docs/handoff/CURRENT_TASK.md`, and `tickets/CEX-002.md`. Developer evidence, state/data, and
unrelated dirty work are excluded.
