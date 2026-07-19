# REVIEW-0010 — MAN-001 CHANGES REQUIRED

**Review type:** Senior mandatory review of MAN-001 after integration
**Reviewed commit (baseline):** `1667662b650d148fbece6b120de9490da0723cc9`
**Review decision:** CHANGES_REQUIRED (MAN-001 remains AWAITING_REVIEW)
**Correction commit (after fixes):** `fix(man-001): enforce atomic immutable dataset publication`
**Reviewer:** Senior Engineer
**Junior (Hermes) scope:** integrate Sr Dev code drop, run validation matrix, records, one local commit. No push.

## Baseline under review

`1667662b650d148fbece6b120de9490da0723cc9` — MAN-001 migration-acceptance tests
(0005 PK flip, partition_json preserved; 4 migration-acceptance groups). Tree clean
at correction start.

## Defects found (7)

| # | Defect | Severity | Required fix |
|---|--------|----------|--------------|
| 1 | Published output files shared the caller's source inode via `os.link` (mutable storage dependency; source rewrite/delete corrupts published data). | HIGH | Copy to a new inode (CoW `copy_file_range` + exclusive streaming fallback); never hard-link; fsync. |
| 2 | Publication built directly in the final dataset directory; a crash mid-build or a crash before finalize could expose a partial/empty final dir or overwrite a pre-existing one. | HIGH | Build in a unique temp stage under `config.temp_dir()`; verify+fsync; atomically `os.rename` into an absent final dir under a no-clobber reservation; never overwrite an existing (incl. empty) final dir. |
| 3 | Relative-path maps (`output_sources`, `specs`, `row_counters`, `row_receipts`) not canonicalized consistently; noncanonical keys could KeyError or diverge; collisions not rejected with a typed error. | MED | Canonicalize all maps via `canonical_relative_path`; reject canonical collisions with a typed `OutputVerificationError`; no KeyError. |
| 4 | Manifest wire schema was not a single source of truth; no generated JSON schema; validation was ad hoc. | MED | Pydantic v2 strict model `DatasetManifestWire` = source of truth; generate `schemas/dataset_manifest.schema.json`; strict validation in `manifest_from_dict`; contract test asserts the checked-in schema matches the generated one. |
| 5 | Catalog idempotence was not exact across all persisted fields; `verify_dataset` did not compare `schema_fingerprint`, `quality_summary_json`, coverage/availability times, `created_at`, `publication_status`, `supersedes_dataset_id`, or file `partition_json`. | HIGH | Exact projection of every persisted field in `_complete_identical_registration`; `verify_dataset` compares all of them; tamper → FAILURE / `CorruptDatasetError`. |
| 6 | Catalog transaction could commit before the on-disk published tree was independently verified; no shared tree-verification module. | HIGH | `verify_published_tree(receipt)` runs (read-only) before the catalog txn; shared module used by both `register_from_receipt` and `verify_dataset`. |
| 7 | Ruff: unused `published` (publisher) and unused `plan2` (test). | LOW | Removed. |

## Applied corrections

- **D1 — `publisher.py`:** removed `os.link`; added `_copy_to_new_inode` (chunked copy to a
  new inode, physically independent of source) used for every output. Rewrote
  `_publish_as_owner` to build in a unique stage dir `stage-{dataset_id}-{pid}-{tid}-{time}`
  under `config.temp_dir()`, fsync, then `os.rename(stage, final_dir)` under a no-clobber
  reservation (`_ReservationLost` on collision → loser reuses). Generic rename `OSError`
  wrapped as `DatasetPublicationError` (never a partial final dir). Removed unused `published`.
- **D2 — `publisher.py`:** atomic-expose protocol; never overwrites a pre-existing final dir
  (incl. empty). `config.temp_dir()` now used for the build area.
- **D3 — `outputs.py`:** canonicalized `output_sources`/`specs`/`row_counters`/`row_receipts`
  via `_normalize_path_keyed_mapping` (typed `TypeVar`); collisions rejected with
  `OutputVerificationError("duplicate canonical logical path in {label}")`. (Sr Dev final fix.)
- **D4 — `schema_model.py` (new) + `parse.py`:** `DatasetManifestWire` strict Pydantic model;
  `validate_manifest_dict()` called at top of `manifest_from_dict`; `generate_schema_json()`
  regenerates `schemas/dataset_manifest.schema.json`.
- **D5 — `catalog_store.py` + `verification.py`:** exact field projection in
  `_complete_identical_registration`; `verify_dataset` compares all persisted fields incl.
  `publication_status` and `supersedes_dataset_id`.
- **D6 — `verify_tree.py` (new) + `catalog_store.py`:** `verify_published_tree(receipt)` runs
  before the catalog txn; shared by `register_from_receipt` and `verify_dataset`.
- **D7 — `tests/test_dataset_manifest.py`:** removed unused `plan2`; renamed monkeypatch
  targets to the new function names.

## Sr Dev drop integrated

`MAN001_typing_fix.zip` → `src/cryptofactors/catalog/dataset/outputs.py` (typing fix only).
Replaced the in-flight Junior canonicalization with the typed `_normalize_path_keyed_mapping`
helper + explicitly-annotated empty defaults, resolving the 4 mypy `assignment` errors.

## Validation (correction commit)

- `mypy` (affected, `--no-incremental`): **Success — no issues in 18 files**.
- `ruff check src tests scripts`: **All checks passed!**
- `pytest tests/catalog/test_man001_correction.py`: **27 passed** (all 7 defect categories).
- Targeted MAN-001: `tests/test_dataset_manifest.py` + `test_man001_duplicate_content.py` +
  `test_man001_migration_acceptance.py`: **31 passed**.
- Full suite: **239 passed** (baseline 208).
- `git diff --check`: **CLEAN**.
- Wheel build: `crypto_multifactor_bot-0.1.0-py3-none-any.whl` built OK.
- `python3 scripts/check_repo_control.py`: **PASS**.

## Unresolved risks

- mypy full-repo still has 46 pre-existing errors **outside** MAN-001 (untouched by this ticket).
- No CLI surface for `verify_dataset`/`publish`; invocation is programmatic only.
- The correction commit is LOCAL only (no push) pending Senior/Engineer re-review of the
  new commit hash.

## Disposition

CHANGES_REQUIRED satisfied by `fix(man-001): enforce atomic immutable dataset publication`.
MAN-001 remains AWAITING_REVIEW; no next ticket authorized.
