# REVIEW-0015 — AUD-001 v1.2.1 gap undercount (WITHDRAWN — fixture error)

**Status:** WITHDRAWN / superseded by REVIEW-0016 (`ACCEPTED`).

**Correction:** The "gap undercount" reported here was **not a production defect**.
The reproduction used a test fixture that built cumulative timestamps from origin `0`
then dropped it with `ts = ts[1:]`, which removed one 100-second inter-row delta, so the
CSV exposed only a single 100s delta while the assertion expected two. The production
spill/`gap_count_against` logic was correct all along (the isolation test already
returned `gap_count == 2`). The fixture bug was fixed in commit `5fac3ac…`
(`tests/audit/test_profiler.py` no longer slices `ts[1:]`), after which
`test_full_mode_gaps_classified_against_final_median` passes with `gap_count == 2` and
`median_cadence_seconds == 1`. No Sr Dev change to `src/cryptofactors/audit/` was required.

The remainder of this record is retained for audit trail only; treat its finding as
resolved-without-code-change.

---

# REVIEW-0015 (original text, retained for history)

**Ticket:** AUD-001 — Schema and coverage profiler
**Implementation reviewed:** commit `64c254d623540d51fbe63b4772d9cf147539d856`
  (AUD-001 v1.2.0 correction, pushed) + Sr drop `AUD001_v121_exact_gaps_fix.zip`
  integrated as `PROFILER_VERSION` `1.2.1` (commit `260eb24…`).
**Verdict / Status:** CHANGES_REQUIRED → **WITHDRAWN** (fixture error, not a defect)

## (Original) Blocking finding — cadence `gap_count` undercount

> WITHDRAWN: this was a test-fixture artifact, not a production bug. See top note.

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

WITHDRAWN. The gap "defect" was a fixture artifact; fixed in `5fac3ac…`. AUD-001
accepted at `5fac3ac…` (see REVIEW-0016). Next ticket authorized: `NONE`.

## (Original) Request to Sr Dev (relay verbatim)

> WITHDRAWN — no Sr Dev change required. Retained for history.
> AUD-001 `gap_count` undercounts by one in FULL mode. Read the code under
> `src/cryptofactors/audit/profiler.py` …
