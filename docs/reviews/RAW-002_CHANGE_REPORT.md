# RAW-002 — Change Report: harden publication-receipt verification against symlink substitution

**Ticket:** RAW-002
**State:** AWAITING_REVIEW
**Next ticket authorized:** NONE
**Next required actor:** Reviewer

## Summary

Integrated the REVIEW-0074 approved source for RAW-002. The verification now:

- Constructs the expected canonical path lexically (no resolution of final component)
- Compares receipt path identity without following symlinks
- Rejects `.` and `..` components in the candidate path before `normpath` normalization
- `lstat`s every root-relative component, rejecting symlinks, missing components, non-directory parents, and non-regular final files
- Only after path validation performs size and SHA-256 verification

Added adversarial regression tests covering final-path symlink substitution, parent-component symlink substitution, lexical `..` rejection, escaping path rejection, missing component, non-directory parent, and non-regular final component. All gates pass.

## Files changed in this submission

- `src/cryptofactors/ingest/raw/paths.py` — `assert_lexical_under_root` traversal rejection before normalization; `assert_store_path_components_lstat` strict component checks
- `src/cryptofactors/ingest/raw/catalog.py` — `verify_publication_receipt` uses lexical path construction and component `lstat`
- `src/cryptofactors/ingest/raw/writer.py` — uses new path safety helpers
- `tests/test_raw_object_writer.py` — adversarial regression tests
- `docs/reviews/REVIEW-0072_RAW-002_SR_SOURCE_AUTHORIZED.md`
- `docs/reviews/REVIEW-0073_RAW-002_SOURCE_TRAVERSAL_CORRECTION_REQUIRED.md`
- `docs/reviews/REVIEW-0074_RAW-002_SOURCE_APPROVED_JR_AUTHORIZED.md`
- `docs/reviews/RAW-002_JR_CONTROL_PUBLICATION_TASK.md`
- `docs/reviews/RAW-002_JR_REVIEW0073_PUBLICATION_TASK.md`
- `docs/reviews/RAW-002_JR_INTEGRATION_TASK.md`
- `docs/reviews/RAW-002_CHANGE_REPORT.md`
- `docs/handoff/CURRENT_TASK.md`
- `README.md`
- `docs/engineering/IMPLEMENTATION_BACKLOG.csv`
- `tickets/RAW-002.md`

## Acceptance gates

```bash
PYTHONPATH=src uv run pytest tests/test_raw_object_writer.py -q --tb=short
# ........................ [100%]
# 30 passed

PYTHONPATH=src uv run ruff check src/cryptofactors/ingest/raw tests/test_raw_object_writer.py
# All checks passed!

PYTHONPATH=src uv run mypy --no-incremental src/cryptofactors/ingest/raw tests/test_raw_object_writer.py
# Success: no issues found in 10 source files

PYTHONPATH=src uv run pytest -q --tb=short
# 470 passed, 1 warning

python3 scripts/check_layer_imports.py
# layer import check passed

python3 scripts/check_repo_control.py
# Repo control check: PASS
```

## Notes

- Defense-in-depth: concurrent filesystem mutation after verification begins remains outside scope
- Shared `canonical_identity` behavior unchanged for writer/catalog callers
- Failures surface as stable `CatalogRegistrationError`; published bytes are never re-hashed against substituted symlink targets