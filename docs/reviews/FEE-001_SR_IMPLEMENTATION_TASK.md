# FEE-001 - SR IMPLEMENTATION TASK

**Actor:** Sr Dev - Grok Build 4.5
**Scope:** production source and migration only
**Next ticket:** `NONE`

## Status

**COMPLETED - SOURCE DROP**

## Workspace Preflight

Before reading broadly or editing, verify:

1. `pwd` is exactly `/home/lars/Crypto_Multifactor_Bot`.
2. `tickets/FEE-001.md` exists locally.
3. This task file exists locally.
4. `git status --short` may contain the Reviewer authorization records, but no conflicting source edits.

If either file is absent or the working directory differs, report the observed path and stop. Do not
search a different clone or infer the task from committed `origin/main`.

## Read Only

- `tickets/FEE-001.md`
- `src/cryptofactors/reference/models.py`
- `src/cryptofactors/reference/store.py`
- `src/cryptofactors/reference/__init__.py`
- `sql/migrations/0006_reference_master.sql`
- `src/cryptofactors/catalog/runner.py`

Consult other production files only when an exact import or migration convention requires it. Do not
reread prior review chains.

## Implement

Make the smallest source change satisfying the ticket:

- add `sql/migrations/0007_reference_fee_schedule.sql`;
- add `FeeEvidenceClass` and immutable `FeeSchedule` models;
- export the new public types;
- add deterministic ID, insertion, contiguous supersession, and exact bitemporal as-of lookup to
  `ReferenceStore`;
- persist fee rates as canonical Decimal strings and reject non-Decimal/non-finite/out-of-range values;
- enforce instrument existence and same-instrument/tier bitemporal non-overlap inside `_atomic`;
- preserve evidence metadata and supersession lineage without mutable defaults;
- return `None` on missing exact instrument/tier lookup, with no fallback.

Follow existing exception, fingerprint, UTC, serialization, transaction, and row-conversion conventions.
Do not alter existing behavior to make the extension easier.

## Prohibited

- Tests, fixtures, docs, tickets, handoff, backlog, README, or review edits.
- Git, commits, pushes, network calls, CLI work, numeric fee defaults, provider-specific values.
- Spread, impact, funding, borrow, FX, route, label, portfolio, or factor code.
- Running tests or claiming integration acceptance.

## Stop

Leave source edits in the shared local worktree. Report only changed source files, the public API added,
and any unresolved implementation concern. Stop for Reviewer inspection.
