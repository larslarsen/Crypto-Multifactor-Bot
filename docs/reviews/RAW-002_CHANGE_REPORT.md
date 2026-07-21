# RAW-002 — Change Report: harden publication-receipt verification against symlink substitution

**Ticket:** RAW-002
**State:** ACCEPTED
**Next ticket authorized:** NONE
**Next required actor:** (none)

## Summary

Integrated the REVIEW-0074 approved source for RAW-002. The verification now:

- Constructs the expected canonical path lexically (no resolution of final component)
- Compares receipt path identity without following symlinks
- Rejects `.` and `..` components in the candidate path before `normpath` normalization
- `lstat`s every root-relative component, rejecting symlinks, missing components, non-directory parents, and non-regular final files
- Only after path validation performs size and SHA-256 verification

Added adversarial regression tests covering final-path symlink substitution, parent-component symlink substitution, lexical `..` rejection, escaping path rejection, missing component, non-directory parent, and non-regular final component.

Accepted per REVIEW-0077. Mypy reports exactly seven pre-existing errors (lines 235-310 in tests/test_raw_object_writer.py, none in RAW-002 source or new tests). Zero-new-diagnostics ratchet accepted for this ticket. All other gates pass with the exact outputs below.

## Files changed in this submission

- `src/cryptofactors/ingest/raw/paths.py` — `assert_lexical_under_root` traversal rejection before normalization; `assert_store_path_components_lstat` strict component checks
- `src/cryptofactors/ingest/raw/catalog.py` — `verify_publication_receipt` uses lexical path construction and component `lstat`
- `tests/test_raw_object_writer.py` — adversarial regression tests
- `docs/reviews/REVIEW-0072_RAW-002_SR_SOURCE_AUTHORIZED.md`
- `docs/reviews/REVIEW-0073_RAW-002_SOURCE_TRAVERSAL_CORRECTION_REQUIRED.md`
- `docs/reviews/REVIEW-0074_RAW-002_SOURCE_APPROVED_JR_AUTHORIZED.md`
- `docs/reviews/RAW-002_JR_CONTROL_PUBLICATION_TASK.md`
- `docs/reviews/RAW-002_JR_REVIEW0073_PUBLICATION_TASK.md`
- `docs/reviews/RAW-002_JR_INTEGRATION_TASK.md`
- `docs/reviews/REVIEW-0075_RAW-002_ADVERSARIAL_EVIDENCE_REQUIRED.md`
- `docs/reviews/RAW-002_JR_FINAL_TEST_TASK.md`
- `docs/reviews/REVIEW-0076_RAW-002_FINAL_TEST_AND_GATES_REQUIRED.md`
- `docs/reviews/RAW-002_JR_FINAL_GATE_TASK.md`
- `docs/reviews/REVIEW-0077_RAW-002_ACCEPTED.md`
- `docs/reviews/RAW-002_JR_ACCEPTANCE_PUBLICATION_TASK.md`
- `docs/reviews/RAW-002_CHANGE_REPORT.md`
- `docs/handoff/CURRENT_TASK.md`
- `README.md`
- `docs/engineering/IMPLEMENTATION_BACKLOG.csv`
- `tickets/RAW-002.md`

## Acceptance gates

```bash
PYTHONPATH=src uv run pytest tests/test_raw_object_writer.py -q --tb=short
# ............................ [100%]
# 28 passed

PYTHONPATH=src uv run ruff check src/cryptofactors/ingest/raw tests/test_raw_object_writer.py
# All checks passed!

PYTHONPATH=src uv run mypy --no-incremental src/cryptofactors/ingest/raw tests/test_raw_object_writer.py
# tests/test_raw_object_writer.py:235: error: Function is missing a return type annotation  [no-untyped-def]
# tests/test_raw_object_writer.py:240: error: Call to untyped function "gen" in typed context  [no-untyped-call]
# tests/test_raw_object_writer.py:257: error: Value of type "Mapping[str, Any] | None" is not indexable  [index]
# tests/test_raw_object_writer.py:267: error: Value of type "Mapping[str, Any] | None" is not indexable  [index]
# tests/test_raw_object_writer.py:280: error: Value of type "Mapping[str, Any] | None" is not indexable  [index]
# tests/test_raw_object_writer.py:305: error: Function is missing a return type annotation  [no-untyped-def]
# tests/test_raw_object_writer.py:310: error: Call to untyped function "gen" in typed context  [no-untyped-call]
# Found 7 errors in 1 file (checked 10 source files)

PYTHONPATH=src uv run pytest -q --tb=short
# 470 passed, 1 warning

python3 scripts/check_layer_imports.py
# layer import check passed

python3 scripts/check_repo_control.py
# Repo control check: PASS
```

Per REVIEW-0077: exact mypy output retained. RAW-002 accepted with zero-new-diagnostics ratchet (no diagnostics in approved source or RAW-002 tests).

## Notes

- Defense-in-depth: concurrent filesystem mutation after verification begins remains outside scope
- Shared `canonical_identity` behavior unchanged for writer/catalog callers
- Failures surface as stable `CatalogRegistrationError`; published bytes are never re-hashed against substituted symlink targets