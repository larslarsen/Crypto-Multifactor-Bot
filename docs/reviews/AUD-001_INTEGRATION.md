# AUD-001 — Implementation Handoff & Validation Evidence

**Ticket:** AUD-001 (Schema and coverage profiler)
**Status:** IN_PROGRESS (implementation landed; awaiting reviewer acceptance)
**Source of truth:** `tickets/AUD-001.md`, `docs/handoff/CURRENT_TASK.md`, AGENTS.md

## Correction drop (v1.2.0 — reviewer CHANGES_REQUIRED resolved)

- Source: Sr Dev Sandbox drop `AUD001_v12_outofcore_fix.zip` (newest in `~/Downloads`,
  dropped after the governance repair at `6ed42c0`). Integrates as `PROFILER_VERSION`
  `1.2.0`; `errors.py` / `__init__.py` unchanged, `models.py` + `profiler.py` revised.
- This drop resolves the four `CHANGES_REQUIRED` findings from `REVIEW-0013`:
  1. **Bounded FULL-mode** — `_PARQUET_BATCH` / `_CADENCE_RESERVOIR` / `_DETAIL_CAP`
     bounds; FULL mode spills exact duplicate-key counts (`_KeySpill`) and exact
     cadence median (`_DeltaSpill`) to SQLite; never `collect()`s a full Parquet
     dataset; SAMPLE mode uses a bounded reservoir.
  2. **Valid MAN-001 statistics** — artifacts stage with verified byte size + SHA-256
     and a stable `_SCHEMA_FINGERPRINT`; summary records the verified identity.
  3. **SHA-256 verification** — `_verify_identity()` checks both `content_sha256` and
     `byte_size` against the file before any staging (verify, not merely record).
  4. **Preserved Parquet physical types** — `_parquet_type_label()` records the native
     Arrow dtype verbatim as `declared_type_label` on each `ColumnProfile`; clearly
     typed columns are not flagged uncertain.
- Integration defects fixed by Hermes (behavior-preserving, to pass repo strict gates,
  same pattern as the v1.0.0 integration): `csv.DictReader[str]` type arg; renamed
  comprehension-leaked locals (`c`→`close_`, `num`→`num_val`) that broke OHLC/type
  assignment under strict mypy; removed an unused `ColumnRole` import; added
  `# type: ignore[import-untyped]` on the `pyarrow` import (repo has no pyarrow stubs);
  re-applied the empty-`{}` Parquet padding in `_write_parquet` (the drop reintroduced
  the same field-less-struct bug).

## Focused test inventory — `tests/audit/test_profiler.py` (11 tests)

Original 7 (sampling vs full, inferred types, impossible-OHLC, mapping roles,
duplicate keys, byte-size mismatch, missing file) plus 4 new finding-encoding tests:
- `test_sha256_mismatch_is_verified_not_just_recorded` — wrong hash (matching size)
  raises `AuditInputError`.
- `test_parquet_preserves_physical_types` — Parquet input records Arrow dtype verbatim
  (`int64`/`double`/`large_string`/`bool`) and `type_uncertainty is False`.
- `test_full_mode_processes_large_csv_without_materializing` — 50k-row CSV profiles in
  FULL with `EXACT` row count (out-of-core spill path runs).
- `test_summary_carries_valid_identity_statistics` — summary records verified identity.
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

## Correction drop v1.2.1 (exact gaps — REVIEW-0015, CHANGES_REQUIRED open)

- Source: Sr Dev Sandbox drop `AUD001_v121_exact_gaps_fix.zip` (newest in `~/Downloads`
  after `64c254d`). Integrates as `PROFILER_VERSION` `1.2.1`; `errors.py` /
  `__init__.py` unchanged, `models.py` + `profiler.py` revised. `_SCHEMA_VERSION`
  bumped to `1.1.0` and `declared_type_label` is now also serialized into the summary
  JSON (makes Parquet physical-type preservation durable in output).
- Intent: gaps classified against the FINAL median via `_DeltaSpill.gap_count_against`
  (bounded SQL `COUNT WHERE delta > 3*median`), replacing the v1.2.0 running-probe
  approximation.
- **Open defect (CHANGES_REQUIRED, REVIEW-0015):** the profiler's reported `gap_count`
  undercounts by one in FULL mode (reproduced: two 100s around a 1s median → expected
  2, profiler returns 1; the spill class itself returns 2 in isolation). Routed to Sr
  Dev; `tests/audit/test_profiler.py::test_full_mode_gaps_classified_against_final_median`
  pins it (currently FAILS on v1.2.1).
- Integration fixes Hermes re-applied (behavior-preserving, strict-gate only): added
  `@dataclass` to `_DeltaSpill` and `_CadenceReservoir` (drop had reverted them →
  runtime `TypeError`); `csv.DictReader[str]`; renamed comprehension-leaked locals
  (`c`→`close_`, `num`→`num_val`); removed unused `ColumnRole` import; pyarrow
  `# type: ignore[import-untyped]`; re-applied the empty-`{}` Parquet padding in
  `_write_parquet`.

## Unresolved risks / notes

- Profiling writes Parquet detail/issues artifacts via `polars`; CSV and Parquet
  input are supported. Other formats raise `AuditFormatError` (by design).
- `profile_candidate` stages artifacts and returns a MAN-001 `PublishPlan` but does
  NOT publish — publication remains the caller's explicit, gated step.
- Full-repo mypy outside AUD-001 (legacy of earlier tickets) is out of scope.
- AUD-001 remains IN_PROGRESS; next ticket authorized: NONE.
