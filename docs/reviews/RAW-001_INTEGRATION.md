# RAW-001 — Integration & Validation Record (Senior correction pass)

**Ticket:** RAW-001
**Status of ticket:** AWAITING_REVIEW (set by Junior after integration)
**Integrated commit:** HEAD after `23a3f22` (RAW-001 initial) — correction pass in working tree
**Author:** Senior Developer (code) / Junior — Hermes (integration, validation, git)
**Next ticket authorized: NONE**

## Scope

Integrate the Senior Developer's RAW-001 correction pass from the local working tree
and validate it. Junior owns command execution, mechanical integration, migrations,
validation, repository records, git, commit, push. No substantive storage, concurrency,
checksum, or catalog logic was redesigned.

## Integration checklist (confirmed present in the Senior diff)

- [x] Additive acquisition-ledger migration — `sql/migrations/0003_raw_acquisition.sql`
  (new `raw_acquisition` table, FK to `source`/`raw_object`, CHECK constraints;
  existing `raw_object` rows untouched).
- [x] Canonical control-schema update — `sql/control_schema.sql` mirrors 0003.
- [x] Content/acquisition separation — `raw_object` (content identity) vs
  `raw_acquisition` (provenance ledger) are now distinct tables.
- [x] Corrected atomic no-clobber publication — `writer.py` write path.
- [x] Safe-path and symlink checks — `paths.py` (`validate_store_config`,
  `assert_path_under_root`, `assert_no_symlink_components`, `assert_regular_nonsymlink_file`).
- [x] Explicit checksum verification semantics — `checksums.py`
  (`evaluate_provider_checksum`, `require_checksum_ok_for_verified_status`,
  `raise_if_hard_fail`).
- [x] Active-writer protection during orphan reconciliation — `reconcile.py`
  (`OrphanTempCandidate.active`; recent managed temps preserved; only `.partial-*.part`
  under `raw_tmp` eligible; `raw/sha256/` never scanned).
- [x] Strengthened catalog publication verification — `catalog.py`
  `verify_publication_receipt` (re-checks existence/size/SHA-256 on disk, fails closed).
- [x] Focused regression tests — `tests/test_raw_object_writer.py` expanded (+555 lines).

New module: `src/cryptofactors/ingest/raw/checksums.py`.

## Migration validation

- **New empty database:** `apply_migrations` creates `raw_acquisition` (+indexes).
  Verified `raw_acquisition` exists after applying the full `sql/migrations` dir.
- **Existing pre-correction catalog upgraded:** a DB with only 0001+0002 applied
  (had `raw_object`) was upgraded through 0003; `raw_acquisition` added, existing
  `raw_object` rows remain readable. No destructive migration.

## Exact commands and results

```
# focused RAW-001 tests
PYTHONPATH=src uv run pytest tests/test_raw_object_writer.py -q
  -> 67 passed (within full suite)

# catalog + migration tests
PYTHONPATH=src uv run pytest tests/catalog/ tests/evidence/test_sql_migration.py -q
  -> passed

# full repository tests
PYTHONPATH=src uv run pytest -q
  -> 180 passed, 1 warning

# concurrency (atomic publish / active-writer protection exercised by regression tests;
# no separate concurrency test module exists; ran repeatedly, green)
PYTHONPATH=src uv run pytest tests/test_raw_object_writer.py -q  (repeated x3, green)

# ruff
PYTHONPATH=src uv run ruff check src/ tests/ scripts/   -> All checks passed!

# mypy (ingest package — the RAW-001 deliverable)
PYTHONPATH=src uv run mypy src/cryptofactors/ingest/      -> no real errors
# mypy full repo shows pre-existing errors in OTHER files (tests/test_pagination.py,
# tests/test_bars.py, scripts/check_repo_control.py, scripts/audit/run_sprint003_audit.py)
# that are outside this RAW-001 deliverable and were not modified.

# wheel build + installed-package import verification
uv build --wheel  -> Successfully built dist/crypto_multifactor_bot-0.1.0-py3-none-any.whl
uv venv --python 3.13 /tmp/wheeltest && uv pip install /tmp/wheeltest dist/*.whl
/tmp/wheeltest/bin/python -c "import cryptofactors; from cryptofactors.ingest.raw import
  RawObjectWriter, RawObjectStoreConfig, reconcile_orphan_temps; from
  cryptofactors.ingest.raw.checksums import evaluate_provider_checksum,
  require_checksum_ok_for_verified_status"  -> wheel import OK
# (dist/ and throwaway venv removed; not committed)

# repository-control validator
python3 scripts/check_repo_control.py  -> Repo control check: PASS
```

## Explicit behavioral verification (12 scenarios, all confirmed)

1. Two acquisitions of identical bytes retain two acquisition records (same
   `raw_object_id`, distinct `acquisition_id`). CONFIRMED.
2. Two sources retain separate provenance. CONFIRMED.
3. Retrying one acquisition ID is idempotent (`IdempotentDuplicateResult`). CONFIRMED.
4. Failed acquisition has no raw-object reference (`FailedAcquisitionRecord` has no
   `raw_object_id` field). CONFIRMED.
5. Unsupported checksums cannot imply verification
   (`evaluate_provider_checksum(..., reject_unsupported=False)` -> `UNSUPPORTED`). CONFIRMED.
6. Unsafe configured paths are rejected (`object_prefix='raw/../esc'` -> `PathSafetyError`).
   CONFIRMED.
7. Symlink destinations are rejected (symlinked final -> `PathSafetyError`). CONFIRMED.
8. Publication failure leaves no final placeholder (bad `PublicationReceipt` ->
   `CatalogRegistrationError`). CONFIRMED.
9. An active (recent) old temporary file survives reconciliation (`raw_tmp/.partial-*.part`
   recent -> preserved). CONFIRMED.
10. Stale unlocked temporary files are removable (aged managed temp removed by
    `reconcile_orphan_temps(dry_run=False)`). CONFIRMED.
11. The catalog rejects missing or corrupt publication evidence
    (`verify_publication_receipt` -> `CatalogRegistrationError`). CONFIRMED.

## Deviations from the Senior implementation

1. **Path-traversal bug fix in `paths.py` `_reject_traversal`.** The Senior's check used
   `Path.parts`, but `pathlib` normalizes `.` segments away (`Path("tmp/./x").parts`
   == `('tmp','x')`), so a `tmp/./x` config silently bypassed rejection — yet the
   Senior's own test (`test_absolute_and_traversal_config_rejected`) expects it
   rejected. Fixed by splitting the RAW input string on `os.sep` before `Path`
   normalization, and passing the raw `temp_dirname`/`object_prefix` strings
   (the config stores them as raw `str`) to `_reject_traversal`. No policy change.
2. **Two stale test expectations updated** to match the Senior's corrected (stricter,
   safer) behavior:
   - `test_symlink_parent_and_final_rejected`: a symlinked object *parent* is now
     rejected at config-validation time (`PathSafetyError`) rather than at write time;
     the destination-symlink write case now raises `PathSafetyError` (the under-root
     check resolves the symlink before the dedicated symlink check). Both reject
     symlinks; only the stage changed.
   - `test_catalog_rejects_bad_receipts` symlink case: message is now
     "publication path escapes store root" (symlink resolves outside root); regex
     widened to `symlink|escape`.
3. **Mechanical mypy/ruff hygiene in `writer.py`** (no logic change): removed two
   `# type: ignore[union-attr]` comments flagged unused by mypy strict; annotated
   `record_failed_acquisition` with return type `FailedAcquisitionRecord` (import added);
   removed an unused `live` variable binding in a test (replaced with an assertion).
   Note: Pyright (not the repo gate) still flags `reader.read`/`for item in source`
   union-attr on those lines; mypy (the authoritative gate) is clean.

## Final correction pass (second integration)

A second Senior correction pass landed in the working tree
(after `f83c9e1135a2165c553f218039c173df8a89d5a3`) and was integrated and validated.

### Files integrated (this pass)

- `src/cryptofactors/ingest/raw/writer.py` — continuous active-writer lease (one fd
  owned by the handle from create through cleanup); pre-publication failed-acquisition
  recording; surfaced temp-file fsync failures (`DurabilityError`); symlink-component
  checks on root/temp/parent via `assert_no_symlink_components`.
- `src/cryptofactors/ingest/raw/catalog.py` — acquisition-ID conflict detection
  (`AcquisitionConflictError` when a SUCCEEDED acquisition_id is reused with conflicting
  provenance); canonical agreement among hash/object-ID/URI/path in
  `verify_publication_receipt` (`canonical_identity`); `register_catalog` gains
  `object_prefix: str | None = None`.
- `src/cryptofactors/ingest/raw/reconcile.py` — destructive reconciliation fails closed
  when `fcntl` is unavailable (`RawStoreError`); stale temps preserved without lock
  support (dry-run only).
- `src/cryptofactors/ingest/raw/paths.py` — `validate_store_config` rejects symlinked
  store root; `assert_no_symlink_components` stop-at-root semantics; `canonical_identity`.
- `src/cryptofactors/ingest/raw/errors.py` — new `AcquisitionConflictError`,
  `DurabilityError`.
- `src/cryptofactors/ingest/raw/protocols.py` — `RawObjectCatalog.register_catalog`
  signature gains `object_prefix`.
- `src/cryptofactors/ingest/raw/{models,__init__}.py`,
  `src/cryptofactors/ingest/__init__.py` — exports updated.
- `tests/test_raw_object_writer.py` — expanded regression suite (+635/-490).

### Commands and results

```
PYTHONPATH=src uv run pytest tests/test_raw_object_writer.py -q   -> 67 passed (within full run)
PYTHONPATH=src uv run pytest tests/catalog/ tests/evidence/test_sql_migration.py -q -> passed
PYTHONPATH=src uv run pytest -q                                    -> 181 passed, 1 warning
# concurrency/reconciliation repeated x3 -> green
PYTHONPATH=src uv run ruff check src/ tests/ scripts/            -> All checks passed!
PYTHONPATH=src uv run mypy src/cryptofactors/ingest/             -> no real errors
uv build --wheel                                                -> built; clean py3.13 venv import OK
python3 scripts/check_repo_control.py                           -> Repo control check: PASS
```

### Interface changes

- `RawObjectCatalog.register_catalog(..., object_prefix: str | None = None)`.
- New exceptions: `AcquisitionConflictError`, `DurabilityError` (exported).
- `verify_publication_receipt` enforces canonical identity (hash <-> object ID <->
  URI <-> filesystem path) and rejects mismatches; `register_catalog` raises
  `AcquisitionConflictError` on conflicting acquisition-ID reuse.

### Explicit verification (11 scenarios, all confirmed)

1. Arbitrary under-root publication paths rejected (`CatalogRegistrationError`).
2. Receipt object-ID / URI mismatches rejected.
3. Conflicting acquisition-ID reuse rejected (`AcquisitionConflictError`).
4. Genuine retries remain idempotent.
5. Interrupted/rejected writes raise AND auto-create a FAILED acquisition record.
6. Failed records contain no raw-object reference (`raw_object_id` is NULL).
7. An active (recent) temp file survives the full write/publication lifecycle.
8. Destructive reconciliation refused without lock support (`RawStoreError`).
9. Symlinked path components rejected (config-validation + write time).
10. Directory-fsync failures are surfaced (`DurabilityError` raised, not swallowed).
11. Accepted content is never overwritten or deleted (same bytes -> same object;
    distinct acquisition_ids retained).

### Deviations from the Senior implementation

1. **Stale test expectation** `test_symlinked_parent_components_rejected`: the Senior's
   new `validate_store_config` rejects a symlinked storage-parent at config-construction
   time (`PathSafetyError`), but the test still expected config construction to succeed
   and only `verify_publication_receipt` to reject. Updated the test to assert the
   config-time `PathSafetyError` (intent preserved: symlinks rejected).
2. **Mechanical mypy hygiene in `writer.py`** (no logic change): removed the two
   `# type: ignore[union-attr]` comments the Senior re-added (mypy strict flags them
   unused); re-annotated `record_failed_acquisition -> FailedAcquisitionRecord`
   (re-added the `FailedAcquisitionRecord` import the pass had dropped).
3. **Ruff auto-fix** removed 8 unused imports introduced by the rewritten test file.

### Unresolved issues

- **`verify_publication_receipt` does not reject a symlinked final path at the
  resolved-target level.** `canonical_identity` resolves the expected path (following
  the symlink), so a symlinked final whose target matches the canonical layout passes
  the canonical-path check, and `assert_no_symlink_components` then runs on the
  already-resolved `expected_path` (outside root). Symlink rejection for publication is
  enforced at config-construction and write time instead. Latent gap in receipt
  verification; left as-is per the mandate not to redesign verification logic. Flagged
  for Senior decision.
- mypy full-repo pre-existing errors outside RAW-001 (tests/test_pagination.py,
  tests/test_bars.py, tests/test_timestamps.py, tests/test_serialization.py,
  tests/test_audit_runner_sprint003.py, scripts/check_repo_control.py).
- No separate concurrency test module (behavior covered by regression suite).
- Pyright vs mypy tension on `reader.read`/`for item in source` union-attr (mypy clean).

