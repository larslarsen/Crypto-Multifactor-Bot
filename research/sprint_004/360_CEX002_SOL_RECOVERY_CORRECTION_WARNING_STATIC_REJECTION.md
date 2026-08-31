# CEX-002 Sol Recovery Correction Warning Static Rejection

- **Date:** 2026-08-31
- **Reviewer:** Lead Quantitative Finance Researcher/Engineer
- **Ticket:** CEX-002
- **Decision:** rejected before integration; lifecycle-only correction authorized
- **Reviewed actor:** Sr Dev - Codex Sol using GPT-5.6-sol High
- **Authorized corrective actor:** Sr Dev - Codex Sol using GPT-5.6-sol High
- **Gate 2:** `IN_PROGRESS`
- **Next ticket:** `NONE`

## Reviewed correction and result

The reviewer statically inspected the Review-359 correction at these exact identities:

- production: 5,032 lines, SHA-256
  `3da4da99b5fbc0880ab81d48c51f1355f7a995362811e45c06f2acae22da4c82`;
- CLI, unchanged: 87 lines, SHA-256
  `9e203790432d412d489120fdef6bcb19831cf10461cecc38e7b1f23c41fb0d1a`;
- test source: 2,518 lines and 57 test functions, SHA-256
  `706f1affb6d9fcb07b81d8deef47a3dabe3a4b12f122dc64b34f68fb32a6ffed`;
- fixtures remain unchanged at Review 358's identities.

Sol ran the one Review-359 command exactly once. All 109 collected cases passed, but the result
was not clean. Three manifest-creation ceiling cases emitted
`PytestUnraisableExceptionWarning`. The complete warning proves that a suspended
`iter_pending()` generator is finalized only after the planner has closed its SQLite connection;
its `finally` then calls `cursor.close()` and raises `sqlite3.ProgrammingError: Cannot operate on
a closed database`.

Sol made no post-command edit or rerun and attests that no other executable/test, network, data,
planner/CLI, acquisition, migration, integration, acceptance, or Git command ran. It did not
access the archive or real generation-0 state/WAL/SHM/content/candidate data. The reviewer
executed no test, Python, planner, SQLite, network, or data command.

## Recovery corrections accepted and preserved

Static inspection accepts Review 359's substantive source direction. Completed recovery now
places a final hook before success, rebinds every held root and nested directory, compares the
named locator/checkpoint/page/manifest/lineage/receipt identities across the boundary, performs a
second bounded authentication, and reauthenticates code and SQLite. Manifest creation and
recovery now enforce explicit compressed, per-row, total-decompressed, and row-count ceilings.
Seven recovery substitution cases and the focused ceiling cases pass, while the unchanged
51,275-row production-shaped case remains green. Preserve those changes.

## Sole blocker - early manifest refusal leaks a suspended SQLite iterator

`_write_private_gzip()` consumes `_iter_manifest_lines()`, which owns `iter_pending()` and its
SQLite cursor. When a creation ceiling raises before the input is exhausted, the consumer closes
its gzip/raw output but does not explicitly close the supplied iterator. The planner later closes
the SQLite connection; delayed generator finalization then reaches `cursor.close()` against that
closed connection and produces the observed unraisable warning. The completed-manifest consumer
has the same lifecycle obligation for both its bounded gzip iterator and current-authority
expected-lines iterator on any early mismatch or ceiling refusal.

Close every owned/supplied manifest iterator deterministically in `finally` on success and on
every error path, while the SQLite connection and cursor are still live. Do not merely suppress
`sqlite3.ProgrammingError` in `iter_pending()`; correct the ownership order. Add focused iterator-
closure regression source if useful. The exact targeted pytest output must contain no warnings,
unraisable exceptions, resource leaks, or traceback.

## Lifecycle-only Sol authorization

Sr Dev - Codex Sol using GPT-5.6-sol High remains the sole authorized actor for this surgical
correction. It may edit only:

- `src/cryptofactors/acquisition/binance_usdm_gate2_revision_candidate.py`; and
- `tests/acquisition/test_binance_usdm_gate2_revision_candidate.py`, only for a focused lifecycle
  regression if required.

The CLI and fixtures must remain unchanged. Sol may use read-only static inspection commands for
the governing documents and these two paths. It may not inspect or touch real generation-0 data
or `~/cmb_archive/`, and performs no network/data operation, standalone planner/CLI, acquisition,
migration, integration, repository-record edit, Git operation, commit, push, or acceptance
command.

After editing, Sol may run exactly one new command:

```text
.venv/bin/python -m pytest tests/acquisition/test_binance_usdm_gate2_revision_candidate.py -q --tb=short
```

Sol stops on a nonzero result or any warning output and makes no post-command patch or rerun. It
reports the exact command and complete output, exact SHA-256 and line count for each edited path,
test-function and collected-case counts, and full scope attestation. A clean zero result is source
feedback only and does not integrate or accept the drop.

Hermes remains unauthorized. No candidate execution, cleanup, generation transition, corrected
acquisition, later gate, model, or next-ticket work is authorized. Gate 2 remains `IN_PROGRESS`;
next ticket remains `NONE`.

## Reviewer publication scope

The reviewer may stage, commit, and push exactly:

- `docs/handoff/CURRENT_TASK.md`;
- `research/sprint_004/360_CEX002_SOL_RECOVERY_CORRECTION_WARNING_STATIC_REJECTION.md`; and
- `tickets/CEX-002.md`.

Developer source/test paths, real state/data, implementation evidence, and every unrelated dirty
path are excluded.
