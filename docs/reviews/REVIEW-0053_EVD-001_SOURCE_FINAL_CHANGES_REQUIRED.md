# REVIEW-0053 - EVD-001 SOURCE FINAL CHANGES REQUIRED

**Ticket:** EVD-001 - Operational Evidence Registry
**Status:** CHANGES_REQUIRED - SR SOURCE ONLY
**Next required actor:** Sr Dev - Grok Build
**Next ticket authorized:** `NONE`
**Date:** 2026-07-20

REVIEW-0052 evidence identity, snapshot ownership, supersession shape, export completeness,
seed-field preservation/atomicity, link idempotence, and CLI payload handling are resolved.
Correct only the remaining items below.

## 1. Temporal provenance remains incomplete

`register_hypothesis` still accepts and persists an arbitrary `created_at` string rather than a
validated fixed-width UTC value. Links can predate their hypothesis version; snapshots can have
`as_of` before hypothesis-version creation or `generated_at` before `as_of`; decisions can predate
their cited snapshot or the event they supersede. These cases create impossible point-in-time
state and can make “current” ordering incorrect.

Normalize/validate every persisted timestamp through the same UTC function and enforce:

- link registration is not before hypothesis-version or evidence registration;
- snapshot `as_of` is not before hypothesis-version creation and `generated_at >= as_of`;
- decision `event_at` is not before snapshot generation/as-of;
- `CORRECT`/`REOPEN` occurs strictly after the superseded event.

## 2. Seed re-import is not fully deterministic/idempotent

When neither `created_at` nor top-level `as_of` exists, seed import uses wall-clock time, so the
same file produces different snapshot/decision identity. Re-import can also rebuild the seed
snapshot after later backdated evidence links change the historical view, then conflict with the
existing deterministic decision ID. Unsupported top-level fields are silently ignored.

Require a deterministic explicit seed timestamp (argument or validated top-level `as_of`), reject
unsupported top-level fields, and make an existing identical seed decision/version a true no-op
without rebuilding identity from subsequently changed registry state. Conflicting seed content or
initial state must still fail closed.

## 3. SQLite operational failures escape the typed CLI boundary

`_connect` maps `sqlite3.IntegrityError` but lets other `sqlite3.Error` subclasses escape. For
example, an uninitialized database raises raw `OperationalError`, while CLI commands catch only
`EvidenceRegistryError`.

Map ordinary SQLite failures to stable `EvidenceRegistryError` after rollback while preserving the
specific invariant messages raised intentionally by repository code. CLI commands must exit
nonzero without traceback. Type the CLI fail helper as non-returning so strict control-flow typing
matches runtime behavior.

## Stop condition

Sr edits production source only and returns the corrected source drop. Preserve all accepted
REVIEW-0052 behavior. No tests, records, Git, commits, pushes, or gate claims. Jr integration
remains unauthorized.
