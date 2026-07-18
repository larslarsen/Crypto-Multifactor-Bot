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

## Unresolved issues

- **mypy full-repo pre-existing errors outside MAN-001:** 66 `error:` lines remain in
  `tests/test_pagination.py`, `tests/test_bars.py`, `tests/test_timestamps.py`,
  `tests/test_serialization.py`, `tests/test_audit_runner_sprint003.py`,
  `scripts/check_repo_control.py`, and other non-MAN-001 modules. These predate and are
  independent of this deliverable; not modified in this commit.
- **Pyright vs mypy tension:** Pyright flags a handful of union-attr / undefined-name
  spots that mypy (the repo gate) accepts. mypy on the MAN-001 package is clean.
- **No CLI:** dataset publication is API-only this ticket, as specified (assumption 7).
