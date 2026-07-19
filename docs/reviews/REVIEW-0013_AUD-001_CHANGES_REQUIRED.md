# REVIEW-0013 — AUD-001 CHANGES_REQUIRED

**Ticket:** AUD-001 — Schema and coverage profiler
**Verdict / Status:** CHANGES_REQUIRED
**Reviewed implementation commit:** `9e1a0fc3e0a5b08b14cee23c1d2dc6a9ab8fcf3d`
**Integration record:** `docs/reviews/AUD-001_INTEGRATION.md`
**Prior review:** none (first review of the committed AUD-001 implementation).
**Reviewer:** Senior Quantitative Finance Researcher/Engineer
**Junior (Hermes) action:** documentation / control-plane record only. No code, schema,
or test changes.

## Blocking findings

The implementation is structurally sound and the acceptance commands pass, but four
reviewer findings must be resolved before acceptance:

1. **Bounded FULL-mode processing** — the streaming full-pass (`ProfileMode.FULL`)
   must stay memory-bounded; confirm the implementation does not materialize the
   entire candidate in RAM and document the bound.
2. **Valid MAN-001 statistics** — profiler-produced artifacts must carry valid
   MAN-001 statistics (correct byte sizes, SHA-256, row counts) so the staged
   `PublishPlan` is internally consistent and verifiable.
3. **SHA-256 verification** — the profiler must verify (not merely record) the
   candidate `content_sha256` against the file bytes, or explicitly document why
   verification is deferred to the caller.
4. **Preserved Parquet physical types** — the Parquet detail/issues artifacts must
   preserve physical column types (no silent coercion that loses precision or
   schema information).

## Evidence

- `pytest tests/audit` (7 focused profiler tests): **7 passed**.
- `ruff check src/cryptofactors/audit tests/audit`: **All checks passed!**
- `mypy --no-incremental src/cryptofactors/audit tests/audit`: **Success: no issues
  found in 5 source files**.
- Full suite: **261 passed, 1 warning**.
- `python3 scripts/check_repo_control.py`: **PASS**.
- The four findings above are recorded on `tickets/AUD-001.md` (Reviewer verdict) and
  are the scope of the forthcoming Sr Dev correction drop.

## Next ticket authorized

`NONE`.

## Disposition

AUD-001 remains `IN_PROGRESS` at `9e1a0fc3e7dd722e9075467faa594af944983c56` with a
`CHANGES_REQUIRED` verdict. Hermes will integrate and validate the Sr Dev correction
drop under the current authorized scope; no production changes in this record.

## Correction drop integrated (post-record)

- Sr Dev Sandbox drop `AUD001_v12_outofcore_fix.zip` integrates as `PROFILER_VERSION`
  `1.2.0`, resolving all four blocking findings above (bounded FULL-mode via SQLite
  spill; valid MAN-001 stats; `_verify_identity` SHA-256 + byte-size verification;
  preserved Parquet physical types via `declared_type_label`).
- 4 new focused tests encode the findings; full AUD-001 acceptance gates pass:
  `pytest tests/audit` → 11 passed; ruff/mypy clean on `src/cryptofactors/audit` +
  `tests/audit`; full suite 271 passed; `python3 scripts/check_repo_control.py` → PASS.
- AUD-001 remains `IN_PROGRESS` awaiting the reviewer's re-acceptance of the corrected
  implementation. Next ticket authorized: `NONE`.
