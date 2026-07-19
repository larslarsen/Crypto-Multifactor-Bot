# AUD-001 — Implementation Handoff & Validation Evidence

**Ticket:** AUD-001 (Schema and coverage profiler)
**Status:** IN_PROGRESS (implementation landed; awaiting reviewer acceptance)
**Source of truth:** `tickets/AUD-001.md`, `docs/handoff/CURRENT_TASK.md`, AGENTS.md

## Deliverable integrated (Sr Dev Sandbox drop)

- `src/cryptofactors/audit/__init__.py` — AUD-001 public API
  (`profile_candidate`, `PROFILER_VERSION`, models, errors).
- `src/cryptofactors/audit/profiler.py` — `profile_candidate()` bounded sampling
  (SAMPLE) and streaming full-pass (FULL) modes; inferred physical schema with
  explicit uncertainty; nulls, distinct counts, timestamp coverage, monotonicity
  / gap heuristics, duplicate-key metrics, impossible-OHLC checks, quality issues.
- `src/cryptofactors/audit/models.py` — typed models (`ColumnProfile`,
  `ProfileSummary`, `ProfileResult`, `DuplicateKeyMetrics`, `OhlcMetrics`,
  `InputIdentity`, enums).
- `src/cryptofactors/audit/errors.py` — audit error hierarchy.

Source: Sr Dev Sandbox drop `AUD001_profiler_impl.zip` (newest in `~/Downloads`,
dropped after the AUD-001 activation commit `5a84f54`). Inspected read-only;
contains only the four `src/cryptofactors/audit/` files (no `.git`, caches, or
unrelated changes). This is the implementation for AUD-001 — distinct from the
accepted `source_audit` toolkit (AUD-002/AUD-003), which does NOT satisfy AUD-001.

## Integration defects fixed (Sr drop, to pass repo strict gates)

The raw drop did not pass `strict = true` mypy / ruff. Minimal,
behavior-preserving fixes applied to `profiler.py`:

1. `csv.DictReader` return annotation — added the required type argument
   `csv.DictReader[str]`.
2. OHLC close local `c` shadowed by a comprehension-leaked `str` variable of the
   same name; renamed to `close_` (resolves `assignment` / `operator` type errors).
3. Removed an unused `ColumnRole` import (ruff F401).
4. `_write_parquet` could not write an empty `{}` `context` dict (polars
   "struct type with no child field"). Padded empty dict values with a dummy key
   so the struct column stays valid; real context content is preserved. This was
   a genuine Sr-code defect that broke profiling whenever a file produced zero
   quality issues.

No behavioral logic of the profiling algorithm was altered.

## Focused test inventory — `tests/audit/test_profiler.py` (7 tests)

1. `test_sample_mode_partial_metrics_and_inferred_types` — SAMPLE mode yields
   `row_count_completeness == PARTIAL`, inferred physical types (int/float/string),
   and a `sample_mode_partial_metrics` INFO issue; artifacts staged (not published).
2. `test_full_mode_exact_and_no_sample_issue` — FULL mode yields
   `row_count_completeness == EXACT` and no sample-mode issue.
3. `test_impossible_ohlc_flagged_not_repaired` — a low>high row is surfaced as an
   OHLC violation (`ohlc.violation_count == 1`); values preserved, never silently fixed.
4. `test_mapping_assigns_roles_and_resolves_ambiguity` — explicit `ColumnMapping`
   assigns `TIMESTAMP`/`OPEN`/`VOLUME` roles and suppresses timestamp/OHLC
   ambiguity issues (no silent guesses).
5. `test_duplicate_keys_detected` — a repeated key column is counted
   (`duplicate_key_count == 1`).
6. `test_byte_size_mismatch_raises` — `InputIdentity.byte_size` mismatch raises
   `AuditInputError` (immutable identity is verified, not trusted blindly).
7. `test_missing_file_raises` — a non-existent candidate path raises `AuditInputError`.

## Validation commands & results

```bash
PYTHONPATH=src uv run pytest tests/audit -q --tb=short
  -> 7 passed

PYTHONPATH=src uv run ruff check src/cryptofactors/audit tests/audit
  -> All checks passed!

PYTHONPATH=src uv run mypy --no-incremental src/cryptofactors/audit tests/audit
  -> Success: no issues found in 5 source files

PYTHONPATH=src uv run pytest -q
  -> 261 passed   (254 prior + 7 new)

python3 scripts/check_repo_control.py
  -> Repo control check: PASS
```

## Unresolved risks / notes

- Profiling writes Parquet detail/issues artifacts via `polars`; CSV and Parquet
  input are supported. Other formats raise `AuditFormatError` (by design).
- `profile_candidate` stages artifacts and returns a MAN-001 `PublishPlan` but does
  NOT publish — publication remains the caller's explicit, gated step.
- Full-repo mypy outside AUD-001 (legacy of earlier tickets) is out of scope.
- AUD-001 remains IN_PROGRESS; next ticket authorized: NONE.
