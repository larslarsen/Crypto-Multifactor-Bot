# REVIEW-0009 — RAW-001 FINAL (Reviewer Acceptance)

**Ticket:** RAW-001 — Content-addressed raw object writer
**Status:** ACCEPTED
**Accepted by:** Reviewer (Engineer)
**Accepted at commit:** `2480e463c9db616d9ce9e378b2516f2fc920e659`
**Integration record:** `docs/reviews/RAW-001_INTEGRATION.md`
**Next ticket authorized: NONE**

## Acceptance

The reviewer (Engineer) accepted the RAW-001 content-addressed raw object writer at
commit `2480e463c9db616d9ce9e378b2516f2fc920e659` on `origin/main`.

## Scope confirmed

Junior integration and validation of the Senior Developer's final RAW-001 correction
pass. No substantive storage, concurrency, checksum, or catalog logic was redesigned.
The correction implements canonical publication identity, acquisition-ID conflict
detection, automatic failed-acquisition recording, continuous writer leases,
fail-closed reconciliation without locking, surfaced durability errors, and symlink
protection during configuration and publication.

## Verification results on record

- Focused RAW-001 tests: 67 passed (`tests/test_raw_object_writer.py`).
- Catalog + migration tests: passed (`tests/catalog/`, `tests/evidence/test_sql_migration.py`).
- Full repository suite: 181 passed, 1 warning.
- Concurrency / reconciliation tests: repeated x3, green.
- Ruff: clean (`src/`, `tests/`, `scripts/`).
- mypy: clean on `src/cryptofactors/ingest/` (the RAW-001 deliverable); pre-existing
  full-repo `mypy` errors outside RAW-001 unchanged and not modified.
- Wheel build + clean Python 3.13 venv import: `RawObjectWriter`, `RawObjectStoreConfig`,
  `reconcile_orphan_temps`, `AcquisitionConflictError`, `DurabilityError` import OK.
- Repository-control validator: PASS.
- Explicit behavioral scenarios (11) confirmed: under-root publication paths rejected;
  receipt object-ID / URI mismatches rejected; conflicting acquisition-ID reuse
  rejected; genuine retries idempotent; interrupted/rejected writes auto-create a FAILED
  acquisition record; failed records contain no raw-object reference; active temp survives
  the write/publication lifecycle; destructive reconciliation refused without lock support;
  symlinked path components rejected; directory-fsync failures surfaced; accepted content
  never overwritten or deleted.

## Defects escalated (not redesigned by Junior)

1. `verify_publication_receipt` does not reject a symlinked final path at the
   resolved-target level: `canonical_identity` resolves the expected path (following the
   symlink), so a symlinked final whose target matches the canonical layout passes the
   canonical-path check; `assert_no_symlink_components` then runs on the already-resolved
   `expected_path` (outside root). Symlink rejection for publication is enforced at config
   construction and write time instead. This requires external post-publication filesystem
   mutation to exploit and does not block RAW-001's core writer/catalog invariants, so it
   becomes a non-active hardening ticket (RAW-002) rather than another correction cycle.

## Next ticket

MAN-001 (dataset manifest fingerprint and publisher) is authorized next, activated by
the Junior after this acceptance.
