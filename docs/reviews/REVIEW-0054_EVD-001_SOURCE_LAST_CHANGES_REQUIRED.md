# REVIEW-0054 - EVD-001 SOURCE LAST CHANGES REQUIRED

**Ticket:** EVD-001 - Operational Evidence Registry
**Status:** CHANGES_REQUIRED - SR SOURCE ONLY
**Next required actor:** Sr Dev - Grok Build
**Next ticket authorized:** `NONE`
**Date:** 2026-07-20

REVIEW-0053 temporal ordering, deterministic seed clock, top-level field rejection, SQLite
operation mapping, and non-returning CLI error flow are implemented. Correct only these remaining
fail-closed gaps.

## 1. Connection setup can still escape raw SQLite errors

`sqlite3.connect(...)` and the initial `PRAGMA foreign_keys = ON` execute before `_connect` enters
its exception-mapping block. Path, permission, open, or PRAGMA failures therefore bypass
`EvidenceRegistryError` and can still produce a CLI traceback.

Map connection creation/setup, transactional operations, commit, and rollback-safe SQLite failures
through the same stable repository error boundary. Preserve intentional `EvidenceRegistryError`
messages and always close a successfully opened connection.

## 2. Seed no-op validation ignores snapshot identity

When the deterministic seed decision already exists, the no-op comparison selects but never
checks `evidence_snapshot_id`. A same-ID event with matching scalar fields but an unrelated or
non-initial snapshot is accepted. The loader also accepts any `registry_version` value.

Validate the supported registry version. For an existing seed decision, verify its referenced
snapshot exists, belongs to the exact hypothesis/version, uses the deterministic seed timestamp,
and represents the intended initial seed state. Do not rebuild it from later registry mutations.
For first-time seed state, fail closed rather than silently treating pre-existing linked evidence
as the empty initial snapshot described by the contract.

## Stop condition

Sr edits production source only and returns the corrected source drop. Preserve all accepted
REVIEW-0052/0053 behavior. No tests, records, Git, commits, pushes, or gate claims. Jr integration
remains unauthorized.
