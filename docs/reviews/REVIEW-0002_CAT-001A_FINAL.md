# REVIEW-0002 — CAT-001A final conformance

**Review date:** 2026-07-18
**Decision:** accepted
**Architecture impact:** none
**ADR required:** no

## Scope

Reviewed the CAT-001A remediation chain that brings CAT-001 into conformance with its
committed acceptance criteria:

- `src/cryptofactors/catalog/runner.py`
- `tests/catalog/test_runner.py`
- `tests/catalog/test_cat001_acceptance_gaps.py`
- `sql/migrations/0001_baseline.sql`
- `sql/migrations/0002_evidence_registry.sql`
- `docs/reviews/CAT-001A_CHANGE_REPORT.md`
- `tickets/CAT-001A.md` (status set to `ACCEPTED`)

## Findings from REVIEW-0001 (all resolved)

1. **Atomicity.** Migrations now apply inside an explicit `BEGIN IMMEDIATE` transaction;
   each statement plus its `migration_history` row commit as one unit; failures roll back
   with no partial schema, data, or history row. Verified by the change report's failed-
   migration and comment-prefixed transaction-control tests.
2. **Strict migration discovery.** Filenames must match `NNNN_descriptive_name.sql`;
   duplicate versions and version gaps are rejected with explicit messages; order is
   deterministic.
3. **Isolated tests.** All migration-runner tests use `tmp_path` (no repository mutations).
4. **Descriptor leak.** `mkstemp()` removed in favor of `tmp_path`.
5. **Concurrency.** A bounded, deterministic second-connection read test under WAL mode
   confirms both connections observe the same `migration_history` rows.

## Acceptance status

| Requirement | Status |
|---|---|
| ordered migration discovery | implemented |
| CLI init/status | implemented |
| filename and SHA-256 history | implemented |
| transactional migration application | implemented |
| foreign keys on runner connections | implemented |
| busy timeout and WAL | implemented |
| changed-checksum rejection | implemented |
| gap rejection | implemented |
| duplicate-version rejection | implemented |
| failed-statement rollback | implemented |
| temporary-database tests | implemented |
| concurrency/read behavior | demonstrated |

## Decision

Accept CAT-001A. Record `**Status:** ACCEPTED` on `tickets/CAT-001A.md`. The catalog
layer is now conformant with its acceptance contract; downstream catalog or raw-data
work may proceed when authorized.

This is a conformance correction, not an architecture change. No ADR was required.
