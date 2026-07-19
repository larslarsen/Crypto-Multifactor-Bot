# REVIEW-0015 — AUD-001 v1.2.1 CHANGES_REQUIRED (gap undercount)

**Ticket:** AUD-001 — Schema and coverage profiler
**Implementation reviewed:** commit `64c254d623540d51fbe63b4772d9cf147539d856`
  (AUD-001 v1.2.0 correction, pushed) + Sr drop `AUD001_v121_exact_gaps_fix.zip`
  integrated as `PROFILER_VERSION` `1.2.1` (commit pending this record).
**Verdict / Status:** CHANGES_REQUIRED
**Reviewer of record:** Hermes (Jr Dev) — integration owner; re-acceptance is the
  Senior Quantitative Finance Researcher/Engineer's exclusive call.

## Blocking finding — cadence `gap_count` undercount

The v1.2.1 "exact gaps" fix intends to classify gaps against the FINAL median via
`cadence_exact.gap_count_against(med_cadence)` (bounded SQL `COUNT WHERE delta > 3*median`).
The `_DeltaSpill` class itself is correct (verified in isolation: feeding
`[100,100,1×98]` returns `gap_count == 2`).

But the profiler's reported `gap_count` undercounts by one. Reproduction with a clean
ISO-datetime cadence of two 100s surrounded by 1s (final median = 1, threshold = 3):

- expected (exact): `gap_count == 2`
- profiler result: `gap_count == 1`, `median_cadence_seconds == 1.0`

The spill stores the deltas; `median()` is correct; yet `gap_count_against(med)` returns
1 inside `profile_candidate` while the same call on the same spill in isolation returns 2.
The defect is in how the gap count is computed/returned within the FULL-mode path
(`profiler.py` ~lines 840-846), not in the spill SQL. The Sr Dev should locate why one
gap is dropped (e.g., off-by-one in the delta feed, a `flush()`/`commit()` ordering
issue, or `gap_count_against` interacting with the median pass) and correct it so
`gap_count` equals the exact count of deltas exceeding `3 * final_median`.

## Coverage for the fix

`tests/audit/test_profiler.py::test_full_mode_gaps_classified_against_final_median`
encodes the expected behavior (two large early deltas against a tiny final median →
`gap_count == 2`). It currently FAILS on v1.2.1, pinning the request. Once Sr Dev
returns a corrected drop and Hermes re-integrates, this test must pass.

## Non-blocking integration notes (Hermes-owned, already applied)

These are behavior-preserving fixes Hermes applied to make the drop pass the repo's
strict gates; they are NOT the requested change and need no Sr Dev action:

- `_DeltaSpill` / `_CadenceReservoir` were plain classes referencing `field()` and
  `cls(path=, conn=)`; added `@dataclass` (otherwise runtime `TypeError`).
- `csv.DictReader[str]` type arg; renamed comprehension-leaked locals
  (`c`→`close_`, `num`→`num_val`) that broke OHLC/type assignment under strict mypy.
- removed unused `ColumnRole` import; added `# type: ignore[import-untyped]` on the
  `pyarrow` import (repo has no pyarrow stubs).
- re-applied the empty-`{}` Parquet padding in `_write_parquet` (the drop had reverted
  the v1.2.0 fix for the same field-less-struct bug).

## Disposition

AUD-001 remains `IN_PROGRESS` at `64c254d…` (v1.2.0 accepted-for-integration; v1.2.1
pending this CHANGES_REQUIRED). Hermes integrated v1.2.1 and committed it so the Sr Dev
can read the exact state from the repo. Await Sr Dev's corrected drop (zip) for Hermes
to apply, then re-run acceptance gates. Next ticket authorized: `NONE`.

## Request to Sr Dev (relay verbatim)

> AUD-001 `gap_count` undercounts by one in FULL mode. Read the code under
> `src/cryptofactors/audit/profiler.py` (FULL-mode cadence path, ~lines 840-846, and
> `_DeltaSpill.gap_count_against`). Do NOT touch tests, docs, schema, migrations, or
> anything outside `src/cryptofactors/audit/`. Return a zip of the corrected
> `profiler.py` (and `models.py` only if needed) for Hermes to apply. The fix must make
> `tests/audit/test_profiler.py::test_full_mode_gaps_classified_against_final_median`
> pass (two large deltas against a tiny final median → gap_count == 2).
