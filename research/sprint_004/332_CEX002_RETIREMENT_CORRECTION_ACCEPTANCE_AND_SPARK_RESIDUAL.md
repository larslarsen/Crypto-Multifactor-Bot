# CEX-002 Retirement Correction Acceptance and Spark Residual

- **Date:** 2026-08-27
- **Reviewer:** Lead Quantitative Finance Researcher/Engineer
- **Ticket:** CEX-002
- **Decision:** senior transaction correction accepted; two mechanical output/test residuals authorized
- **Authorized actor:** Implementation Dev - Codex Spark High
- **Gate 2:** in progress; rejected real store remains untouched
- **Next ticket:** `NONE`

## Corrected return review

The reviewer inspected Grok's Review-331 correction once without running commands or tests:

- module SHA-256 `8e74a6f984ea2ec61a7e2b459e8e8f6c61c199ef5f9233208ac6ea92599bc344`,
  1,823 lines;
- CLI SHA-256 `6529cb3d0aa0686d0e389b1c5505cccf8022698d2f175fc44584f7f8ec6bb9df`,
  117 lines; and
- test SHA-256 `286210102b54054597c34f91b7346214b6e8a833227807c7fdc8dfd21edd26e6`,
  1,452 lines and 60 test functions.

Only the three authorized paths changed. The authority, acquisition files, governance, and
real Gate-2 tree remain unchanged. No command or test result is accepted.

The senior correction closes Review 331's architecture blockers. Receipt and SQLite semantic
proof use authority-matched no-follow descriptors, SQLite opens the proved state-file
descriptor immutable/query-only, active and lock names are rebound immediately before rename,
the new parent is rebound before and after rename, and the destination is rebound to the
post-proof descriptor. Replacement-race tests cover each boundary. Receipt output is explicitly
written and flushed, failed retirement output is indeterminate, SQLite failures are bounded
pre-rename, the foreign-key fixture is valid, and the required production-authority,
pre-rename-`fsync`, descriptor-SQLite, output, ASCII, and formatting corrections are present.

The module is accepted unchanged at the identity above. The CLI and test require only the
mechanical residual below before integration.

## Exact Spark residual

Spark may edit only:

- `scripts/research/retire_binance_usdm_harmonic_gate2.py`; and
- `tests/acquisition/test_binance_usdm_harmonic_gate2_retirement.py`.

Make exactly these bounded corrections:

1. In `_emit`, catch `ValueError` together with `BrokenPipeError` and `OSError` around stdout
   write/short-write/flush. Preserve the existing command-dependent exit: retirement output
   failure is `EXIT_INDETERMINATE`; inspection output failure is `EXIT_SAFE`.
2. In `test_integrity_check_failure_is_rejected`, use a bounded `match="SQLite"` (or include
   `SQLite write probe failed unexpectedly`) so the test accepts every intended bounded
   pre-rename SQLite rejection while retaining the exact exception-class and non-indeterminate
   assertions.
3. Add `test_cli_retire_flush_failure_is_indeterminate`, mirroring the existing retirement
   write-failure test with `_BrokenWriter(fail_flush=True)`. Assert exit
   `EXIT_INDETERMINATE`, bounded retirement-receipt error text, active source absence, and exact
   retired destination presence.

Preserve every other byte. Do not edit the accepted module, authority, acquisition files,
governance, configuration, or data. Do not run commands/tests and do not use Git. Return the
CLI/test SHA-256 values and line counts plus test-function count.

Integration, Ruff, pytest, control, real `inspect`, retirement, planning, acquisition, later
gates, and next-ticket work remain unauthorized. Gate 2 remains `IN_PROGRESS`; next ticket
remains `NONE`.

## Reviewer publication scope

The reviewer may stage, commit, and push exactly this review,
`docs/handoff/CURRENT_TASK.md`, and `tickets/CEX-002.md`. Developer source/test paths,
ignored state/data, and unrelated dirty work are excluded.
