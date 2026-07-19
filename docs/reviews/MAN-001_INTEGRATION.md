# MAN-001 — Integration & Validation Record

**Ticket:** MAN-001 — Dataset manifest fingerprint and publisher
**Status of ticket:** AWAITING_REVIEW (set by Junior after integration)
**Integrated commit:** HEAD at `8fdac08e10c91dd8ac14f94fd821aeaa4ad36378` (MAN-001
activation) — Senior implementation in working tree
**Author:** Senior Developer (Grok Build, code) / Junior — Hermes (integration,
validation, git, records)
**Next ticket authorized: NONE**

## Scope

Integrate the Senior Developer's MAN-001 implementation (immutable dataset-manifest
publication) from the local working tree and validate it. Junior owns command
execution, mechanical integration, migrations, validation, repository records, git,
commit, push. No substantive catalog/storage/persistence/lineage logic was redesigned.

## Files integrated

- `sql/migrations/0004_dataset_publication.sql` — NEW additive migration: adds
  `publication_status`, `schema_fingerprint`, `quality_summary_json`, `publication_uri`
  columns to `dataset` (all with defaults / nullable) + two indexes. No destructive
  operations; mirrors `sql/control_schema.sql`. Auto-discovered by the migration runner
  (`_discover_migrations` globs `*.sql`, sorted) — no registration-code change needed.
- `sql/control_schema.sql` — canonical schema updated to match 0004.
- `src/cryptofactors/catalog/__init__.py` — exports the new dataset package
  (`DatasetManifest`, `DatasetPublisher`, `DatasetStoreConfig`, `PublishPlan`,
  `SqliteDatasetCatalog`, `verify_dataset`).
- `src/cryptofactors/catalog/dataset/` — NEW package:
  - `models.py` — canonical manifest model, `DatasetStoreConfig`, `PublishPlan`,
    `OutputFileSpec`, statistics, typed results.
  - `canonicalize.py` — deterministic canonical JSON, dataset ID / manifest SHA-256
    fingerprint, identity payload.
  - `paths.py` — deterministic dataset-identity path, safe-path helpers.
  - `outputs.py` — streaming SHA-256/size, symlink/regular-file checks.
  - `catalog_store.py` — `SqliteDatasetCatalog` (dataset, outputs, lineage edges,
    schema/transform/code/config identities, supersession, recovery-safe registration).
  - `lineage.py` — raw-object and upstream-dataset edges, cycle detection.
  - `publisher.py` — atomic stage → rename publication, idempotent existing-dataset
    verification, durability surfacing, safe cleanup.
  - `verification.py` — `verify_dataset` load/recompute/verify API.
  - `errors.py` — typed exceptions (invalid manifest, fingerprint mismatch, missing/
    unexpected output, hash/size/row mismatch, unsafe path, corrupt dataset, missing
    input, invalid lineage, publication/durability failure, recoverable registration).
- `tests/test_dataset_manifest.py` — NEW focused synthetic test suite (15 tests).

## Migration validation

- **New empty database:** `apply_migrations` (full `sql/migrations` dir) adds the
  0004 columns; `dataset` gains `publication_status` (default `REGISTERED`),
  `schema_fingerprint`, `quality_summary_json`, `publication_uri`.
- **Existing pre-MAN-001 catalog upgraded:** a DB with only 0001-0003 applied (had a
  `dataset` row) was upgraded through 0004; new columns added, the existing dataset row
  preserved (quality_status OK, publication_status REGISTERED). No destructive migration.

## Exact commands and results

```
# focused MAN-001 tests (migrations applied through 0004 by test fixtures)
PYTHONPATH=src uv run pytest tests/test_dataset_manifest.py -q   -> 15 passed

# full repository tests
PYTHONPATH=src uv run pytest -q                                    -> 196 passed, 1 warning

# ruff
PYTHONPATH=src uv run ruff check src/ tests/ scripts/            -> All checks passed!
  (ruff --fix removed 14 unused imports from the new test file)

# mypy on the MAN-001 deliverable
PYTHONPATH=src uv run mypy src/cryptofactors/catalog/            -> no real errors
  (full-repo `mypy .` still shows 66 pre-existing errors in OTHER files outside MAN-001;
   none in src/cryptofactors/catalog/dataset/)

# wheel build + clean installed-package import verification
uv build --wheel  -> Successfully built dist/crypto_multifactor_bot-0.1.0-py3-none-any.whl
uv venv --python 3.13 /tmp/wt && uv pip install /tmp/wt dist/*.whl
/tmp/wt/bin/python -c "from cryptofactors.catalog import (DatasetManifest,
  DatasetPublisher, DatasetStoreConfig, PublishPlan, SqliteDatasetCatalog,
  verify_dataset)"  -> wheel import OK
# (dist/ and throwaway venv removed; not committed)

# repository-control validator
python3 scripts/check_repo_control.py                           -> Repo control check: PASS
```

## Junior integration assumptions (carried forward from Senior handoff)

1. Apply migrations through 0004 before running MAN-001 tests. (Done — migration runner
   applies 0001-0004; test fixtures build a fresh DB with all four.)
2. RAW-001 raw objects must exist in catalog for RAW_OBJECT dependencies
   (`raw_<64 hex>`). (Handled inside the suite; focused tests seed raw objects where a
   manifest declares raw-object inputs.)
3. Declared `OutputFileSpec.rows` is an explicit boundary, not inferred from parquet/csv.
   (Honored — publisher validates declared rows against the caller-supplied value; it
   does not read parquet/csv internals.)
4. `statistics.row_count` / `byte_size` must equal sums over output specs. (Enforced by
   the model/canonicalization; the suite covers it.)
5. Concurrent publishers of identical content converge on one `dataset_id` via rename
   race + verify. (Covered by the concurrent-identical-publisher test.)
6. Do not "fix" by loading full files into memory, overwriting datasets, or registering
   catalog before filesystem verification. (Honored — publisher streams; registers only
   after filesystem verification.)
7. Optional CLI wiring is deferred (not in this ticket).

## Deviations from the Senior implementation

1. **Mechanical mypy typing fix in `publisher.py`:** `_publish_new` was annotated
   `sources: dict[str, Path]` but the caller passes
   `PublishPlan.output_sources: Mapping[str, Path]`, producing an `arg-type` error.
   Widened the parameter to `Mapping[str, Path]` (the body only subscript-reads it) and
   added `from typing import Mapping`. No logic change; matches the model's declared
   type.
2. **Ruff auto-fix:** removed 14 unused imports introduced by the new test file.

No substantive storage, persistence, locking, lineage, or catalog logic was redesigned.

## Correction pass (second integration)

A second Senior correction pass landed in the working tree (after
`f9e62aeba9cc328270e8d1fe9a5a576b4c05aaba`) and was integrated and validated.

### Files integrated (this pass)

- `src/cryptofactors/catalog/dataset/parse.py` — NEW strict independent manifest parser
  (`load_manifest_bytes`, `load_manifest_file`) used by verification to recompute
  identity from on-disk bytes.
- `src/cryptofactors/catalog/dataset/canonicalize.py` — deterministic ordering,
  retry-stable manifest construction, logical output paths in identity, independent
  identity recomputation.
- `src/cryptofactors/catalog/dataset/catalog_store.py` — registration transaction order,
  strict idempotence, supersession validation, typed verified publication receipt.
- `src/cryptofactors/catalog/dataset/verification.py` — independent manifest parsing +
  identity recomputation, exact catalog/output/lineage comparison, verification without
  an expected manifest.
- `src/cryptofactors/catalog/dataset/{models,errors,outputs,paths,publisher,__init__}.py`
  — `DatasetPublicationReceipt`, `RowCountPolicy`/`RowCountReceipt`, `SupersessionError`,
  lexical symlink-safe canonical paths, exact accepted-tree verification.
- `src/cryptofactors/catalog/__init__.py` — exports `DatasetPublicationReceipt`.
- `tests/test_dataset_manifest.py` — expanded regression suite (+533/-…).

### Commands and results

```
PYTHONPATH=src uv run pytest tests/test_dataset_manifest.py -q   -> 18 passed (1 excluded, see below)
PYTHONPATH=src uv run pytest tests/catalog/ tests/evidence/test_sql_migration.py -q -> passed
PYTHONPATH=src uv run pytest -q                                    -> 199 passed, 1 warning
# concurrent publication repeated x5: test_concurrent_publish FAILED all 5 (see unresolved)
PYTHONPATH=src uv run ruff check src/ tests/ scripts/            -> clean
PYTHONPATH=src uv run mypy src/cryptofactors/catalog/ tests/test_dataset_manifest.py -> no real errors
uv build --wheel                                                -> built; clean py3.13 venv import OK
python3 scripts/check_repo_control.py                           -> Repo control check: PASS
```

### Interface changes

- New public types: `DatasetPublicationReceipt`, `RowCountPolicy`, `RowCountReceipt`,
  `SupersessionError`; new `load_manifest_bytes` / `load_manifest_file` parse helpers.
- `verify_dataset` supports `expected_manifest: DatasetManifest | None` (verification
  works without an expected manifest).

### Explicit verification (scenarios, all confirmed except concurrent convergence)

- Two identical publications without fixed `created_at` are idempotent.
- Changing only an output logical path changes identity.
- Reversed equivalent manifests remain byte-identical.
- Declared but incorrect row counts fail.
- An existing empty final directory is never overwritten.
- Symlinked prefix components are rejected.
- Unexpected dataset files fail verification.
- Any manifest byte change fails verification.
- Verification works without an expected manifest.
- Dataset ID and manifest fingerprint are independently recomputed.
- Catalog output and lineage differences are detected.
- Direct unverified catalog registration is rejected (`register_from_receipt` requires
  the published tree; raw catalog insert path not exposed).
- Missing/self supersession is rejected (see deviation on boundary exception type).
- Concurrent identical registration convergence: **NOT met** (see unresolved issue 1).

### Deviations from the Senior implementation (mechanical, no logic change)

1. **Missing-supersession boundary exception.** The Sr Dev's `publish()` publishes the
   immutable files first, then registration fails and is surfaced as
   `RecoverableDatasetCatalogError` (per the spec: catalog-registration failure after
   publication returns a typed recoverable error). The test originally asserted bare
   `SupersessionError` from `pub.publish(bad)`. Updated the test to expect
   `RecoverableDatasetCatalogError` (the rejection still holds; the immutable tree is
   retained for idempotent retry). The direct `_validate_supersession` self-supersession
   assertion still expects bare `SupersessionError` and passes.
2. **Mechanical mypy hygiene** (no logic change):
   - `canonicalize.py`: `_canonical_partition` annotated result to clear `no-any-return`;
     removed two unused `# type: ignore` comments.
   - `verification.py`: `row_counters: dict[Any, Any] | None`; added `from typing import Any`.
   - `tests/test_dataset_manifest.py`: replaced `**common` dict unpacking into
     `identity_payload` (mypy cannot verify `**dict` kwargs) with a typed `_common_payload`
     helper using explicit named arguments; added `from typing import Any`; added the
     `RecoverableDatasetCatalogError` import.

### Unresolved issues

1. **`test_concurrent_publish` fails deterministically (5/5).** The Sr Dev's
   `_publish_new_no_clobber` uses `os.mkdir(final_dir)` (empty directory) then populates;
   a concurrent identical publisher that hits `FileExistsError` before `manifest.json`
   is written raises `DatasetPublicationError('final dataset path exists but is
   incomplete (concurrent race)')` or `CorruptDatasetError('manifest.json missing or
   unsafe')` instead of waiting/retrying. The spec required rename-based atomic publish
   (stage → atomic rename → verify) so concurrent identical publishers converge on one
   `dataset_id`. This is a substantive publication-atomicity gap; fixing it (rename-based
   swap and/or retry-on-incomplete) is outside Junior mechanical scope and is flagged for
   Senior decision. All other MAN-001 behaviors (idempotent retry, no-clobber, symlink
   rejection, exact verification, independent recomputation, catalog idempotence,
   supersession rejection) pass.
2. **mypy full-repo pre-existing errors outside MAN-001:** remain in non-MAN-001 modules;
   not modified.
3. **Pyright vs mypy tension:** Pyright flags union-attr / `**dict` / undefined-name
   spots that mypy (the gate) accepts. mypy on the MAN-001 package + tests is clean.
4. **No CLI:** dataset publication is API-only this ticket.

## Concurrent-publication correction (third integration)

A third Senior correction pass landed in the working tree (after
`62710afbaa33565596b8cd5d712bb4fa26896ece`) and was integrated and validated. This pass
replaces the `os.mkdir`-then-populate race with a bounded concurrent-safe reservation
protocol that closes the `test_concurrent_publish` gap.

### Files integrated (this pass)

- `src/cryptofactors/catalog/dataset/publisher.py` — rewritten publish path:
  `manifest.json` is the final acceptance marker; outputs are written no-clobber before
  the manifest; `_ensure_published` owns the reservation (exclusive `os.mkdir`) or waits
  with exponential backoff (bounded by `publication_wait_seconds`) and verifies+reuses a
  completed identical dataset; only the owner cleans its own incomplete reservation
  (never another publisher's completed dataset); losers time out as
  `DatasetPublicationInProgressError`. Catalog registration stays after completed
  publication verification.
- `src/cryptofactors/catalog/dataset/models.py` — `DatasetStoreConfig` gains
  `publication_wait_seconds`, `publication_initial_backoff_seconds`,
  `publication_max_backoff_seconds` (validated in `__post_init__`).
- `src/cryptofactors/catalog/dataset/errors.py` — new `DatasetPublicationInProgressError`
  (subclass of `DatasetPublicationError`).
- `src/cryptofactors/catalog/dataset/__init__.py` — exports `DatasetPublicationInProgressError`.
- `tests/test_dataset_manifest.py` — added concurrent tests: `test_concurrent_publish`
  (3 workers), `test_high_contention_publication` (8 workers),
  `test_loser_waits_for_manifest_before_reuse`, `test_loser_retries_after_owner_cleanup`,
  `test_permanently_incomplete_reservation_times_out`.

### Concurrent repetition results

- `test_concurrent_publish` (3 identical publishers): **25/25 passed** (bounded
  wait + reuse; exactly one dataset, all callers get the same dataset_id/manifest hash).
- `test_high_contention_publication` (8 identical publishers): **5/5 passed**; exactly
  one dataset published, all 8 callers converge on one dataset_id.
- `test_loser_waits_for_manifest_before_reuse`: **5/5 passed** (loser waits, then reuses
  the owner's completed dataset; `reused_existing=True`).
- `test_permanently_incomplete_reservation_times_out`: passes (owner that never writes
  the manifest is cleaned by itself; a late loser times out safely as
  `DatasetPublicationInProgressError`; no catalog row references the incomplete dataset).

### Commands and results

```
PYTHONPATH=src uv run pytest tests/test_dataset_manifest.py -q   -> 24 passed
PYTHONPATH=src uv run pytest tests/catalog/ tests/evidence/test_sql_migration.py -q -> passed
PYTHONPATH=src uv run pytest -q                                    -> 205 passed, 1 warning
# test_concurrent_publish x25 -> 25 passed; test_high_contention_publication x5 -> 5 passed
PYTHONPATH=src uv run ruff check src/ tests/ scripts/            -> clean
PYTHONPATH=src uv run mypy src/cryptofactors/catalog/ tests/test_dataset_manifest.py -> no real errors
uv build --wheel                                                -> built; clean py3.13 venv import OK
python3 scripts/check_repo_control.py                           -> Repo control check: PASS
```

### Explicit verification (all confirmed)

- No concurrent identical publisher receives an incomplete-dataset error.
- Exactly one immutable dataset is published.
- All successful callers receive the same dataset ID and manifest hash.
- Failed owners clean their own incomplete reservations.
- Non-owners never remove another process's publication.
- A permanently incomplete reservation times out safely (`DatasetPublicationInProgressError`).
- No catalog row references an incomplete dataset.

### Deviations from the Senior implementation (mechanical, no logic change)

1. **`test_existing_empty_final_directory_rejected`:** the new protocol treats a
   pre-existing empty/incomplete `final` directory as a potential reservation and waits
   (bounded) before rejecting. The test originally asserted immediate
   `CorruptDatasetError`; updated it to expect `DatasetPublicationInProgressError` with
   `publication_wait_seconds=0.0` (immediate timeout). The "rejected" intent is
   preserved; the rejection is now via the bounded-wait timeout, matching the protocol.
2. **`test_loser_waits_for_manifest_before_reuse`:** the `owner()` thread used a
   `SqliteDatasetCatalog` opened in the main thread, raising SQLite "object created in a
   thread" `ProgrammingError` under contention. Fixed by opening the catalog/publisher
   inside `owner()` (per-thread), mirroring the already-correct `loser()` path. Typed
   `results` as `list[tuple[str, DatasetPublishResult]]` and imported
   `DatasetPublishResult` to clear mypy index errors. Pure fixture/synchronization fix.

### Unresolved issues

- **mypy full-repo pre-existing errors outside MAN-001:** 46 `error:` lines remain in
  non-MAN-001 modules (down from 66 after this pass fixed several); not modified.
- **Pyright vs mypy tension:** Pyright flags spots mypy (the gate) accepts. mypy on the
  MAN-001 package + tests is clean.
- **No CLI:** dataset publication is API-only this ticket.

## dataset_file PK correction (fourth integration — MAN001_fix_patch.zip)

The Senior's MAN-001 duplicate-content schema correction was delivered out-of-band as
`/home/lars/Downloads/MAN001_fix_patch.zip` (after the Engineer noted the correction was
missing from `69e856c…`). Integrated and validated.

### Delivered artifacts vs repo

The zip contained four files. Two were real and two were illustrative stubs for a
fictional API that does not exist in this repo:

- `sql/migrations/0005_fix_dataset_file_pk.sql` — REAL migration; adopted with one
  correction (see deviations): it must preserve the live `partition_json` column, which
  the Senior's stub DDL silently dropped.
- `sql/control_schema.sql` — Senior's copy was a partial stub (only the `dataset_file`
  table). The real `sql/control_schema.sql` was edited in place: PK flipped to
  `(dataset_id, storage_uri)`, `partition_json` preserved, redundant `UNIQUE
  (dataset_id, storage_uri)` removed (now the PK), and `idx_dataset_file_sha256` added.
- `src/catalog/registration.py` — STUB referencing a fictional `catalog.control` /
  `register_dataset_file` API. NOT integrated. The real registration path is
  `SqliteDatasetCatalog.register_from_receipt` (via `DatasetPublisher.publish`), which
  already writes `storage_uri` and is unchanged; the PK flip is carried entirely by the
  schema/migration.
- `tests/catalog/test_man001_duplicate_content.py` — STUB using the fictional
  `Catalog.register_dataset_file` / `list_dataset_files`. NOT integrated as-is. Rewritten
  as a real regression test against the shipped API (see below).

### Files integrated (this pass)

- `sql/migrations/0005_fix_dataset_file_pk.sql` (NEW) — copy `dataset_file` into
  `dataset_file_new` with `PRIMARY KEY (dataset_id, storage_uri)`, preserving
  `partition_json`; swap; re-add `idx_dataset_file_sha256`. Auto-discovered by the glob
  migration runner (no registration edit).
- `sql/control_schema.sql` — `dataset_file` PK → `(dataset_id, storage_uri)`.
- `tests/catalog/test_man001_duplicate_content.py` (NEW) — three regression tests:
  duplicate content at two logical paths → 2 rows retained; identical re-register
  idempotent (no extra rows); schema-level proof that identity is `(dataset_id,
  storage_uri)` (same content different path allowed; same uri + different content → PK
  violation).

### Commands and results

```
PYTHONPATH=src uv run pytest tests/catalog/test_man001_duplicate_content.py -q -> 3 passed
PYTHONPATH=src uv run pytest tests/catalog/ tests/evidence/test_sql_migration.py tests/test_dataset_manifest.py -q -> passed
PYTHONPATH=src uv run pytest -q                                    -> 208 passed, 1 warning
PYTHONPATH=src uv run ruff check src/ tests/ scripts/            -> clean
PYTHONPATH=src uv run mypy src/cryptofactors/catalog/ tests/catalog/test_man001_duplicate_content.py tests/test_dataset_manifest.py -> no real errors
python3 scripts/check_repo_control.py                           -> Repo control check: PASS
```

### Deviations from the Senior patch (mechanical, no logic change)

1. **Preserved `partition_json`.** The Senior's `0005` DDL and `control_schema.sql` stub
   dropped `partition_json`, which the live `dataset_file` (0001_baseline) carries. The
   integrated migration and schema keep `partition_json` so no column/data is lost on
   upgrade.
2. **`control_schema.sql` edited in place** rather than overwritten with the partial stub
   (which omitted every other table). Only the `dataset_file` block changed.
3. **`src/catalog/registration.py` and the fictional-API test were not integrated** — they
   target a `catalog.control.Catalog` module that does not exist. The equivalent behavior
   is covered by the real regression test using `SqliteDatasetCatalog.register_from_receipt`.
   `catalog_store.py` required no change (its `INSERT` already includes `storage_uri` and
   `partition_json`; re-registration idempotence already rides the `IntegrityError` path).

### Unresolved issues

- Same as prior passes: mypy full-repo pre-existing errors outside MAN-001 (46);
  Pyright vs mypy tension; no CLI.

---

## Correction pass — Senior review (REVIEW-0010, CHANGES_REQUIRED)

**Baseline reviewed:** `1667662b650d148fbece6b120de9490da0723cc9`
**Correction commit:** `fix(man-001): enforce atomic immutable dataset publication` (LOCAL, no push)
**Trigger:** Senior review found 7 defects (D1–D7) in the reviewed commit.

### Defects addressed

1. Published outputs shared the caller's source inode via `os.link` → replaced with an
   exclusive copy to a new inode (`_copy_to_new_inode`); published bytes are now physically
   independent of source.
2. Publication built directly in the final dir → rewritten to a unique temp stage under
   `config.temp_dir()`, fsync, then atomic `os.rename` into an absent final dir under a
   no-clobber reservation; never overwrites a pre-existing (incl. empty) final dir.
3. Relative-path maps not canonicalized consistently → all maps canonicalized via
   `_normalize_path_keyed_mapping`; canonical collisions rejected with a typed error (Sr Dev fix).
4. Manifest wire schema not a single source of truth → Pydantic v2 strict model
   `DatasetManifestWire` = source of truth; `schemas/dataset_manifest.schema.json` regenerated;
   strict validation in `manifest_from_dict`; contract test asserts parity.
5. Catalog idempotence not exact + `verify_dataset` omitted fields → exact projection of every
   persisted field (incl. `publication_status`, `quality_summary_json`, coverage/availability
   times, `created_at`, `supersedes_dataset_id`, file `partition_json`); tamper → FAILURE /
   `CorruptDatasetError`.
6. Catalog txn could commit before the on-disk tree was verified → `verify_published_tree`
   (new shared module) runs before the txn; used by both `register_from_receipt` and
   `verify_dataset`.
7. Ruff hygiene → removed unused `published` and unused `plan2`.

### Sr Dev drop integrated

`MAN001_typing_fix.zip` → `src/cryptofactors/catalog/dataset/outputs.py` (typing fix only).
Resolved the 4 mypy `assignment` errors in the canonicalization path.

### Validation commands and results (correction commit)

```text
PYTHONPATH=src uv run mypy --no-incremental --cache-dir=/tmp/mc src/cryptofactors/catalog/ tests/test_dataset_manifest.py tests/catalog/test_man001_duplicate_content.py tests/catalog/test_man001_correction.py
    -> Success: no issues found in 18 source files

PYTHONPATH=src uv run ruff check src tests scripts
    -> All checks passed!

PYTHONPATH=src uv run pytest tests/catalog/test_man001_correction.py -q
    -> 27 passed   (all 7 defect categories covered)

PYTHONPATH=src uv run pytest tests/test_dataset_manifest.py tests/catalog/test_man001_duplicate_content.py tests/catalog/test_man001_migration_acceptance.py -q
    -> 31 passed

PYTHONPATH=src uv run pytest -q
    -> 239 passed, 1 warning

git diff --check
    -> CLEAN

uv build --wheel
    -> Successfully built dist/crypto_multifactor_bot-0.1.0-py3-none-any.whl

python3 scripts/check_repo_control.py
    -> Repo control check: PASS
```

### Result

All 7 defects corrected and validated. MAN-001 remains AWAITING_REVIEW; no next ticket
authorized. Correction commit is LOCAL (no push) pending Senior/Engineer re-review.
