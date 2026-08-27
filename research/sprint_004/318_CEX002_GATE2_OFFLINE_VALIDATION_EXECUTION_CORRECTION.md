# CEX-002 Gate-2 Offline Validation Evidence Correction

- **Date:** 2026-08-27 UTC
- **Actor:** Jr Dev — Hermes
- **Ticket:** CEX-002
- **Corrects:** record 316, commit `029487bac6cfa1435832a6396e130cff613e5233`
- **Gate 2:** in progress; no real plan or acquisition authorized
- **Next ticket:** `NONE`

## Corrections

Record 316 incorrectly described Review 308's initial focused Ruff result as a pass. The
correct history is:

- Review 308 focused Ruff ran once and exited `1`, reporting three findings: unused
  `EXIT_UNSAFE_STATE`, unused `dataclasses.replace`, and unused `content_inode`.
- Review 311 accepted the mechanical cleanup. The exact integration commit was
  `61aada40abe9efe85bd7aa0892413656ef06fb30` (`61aada4`), containing only the source and
  CLI cleanup paths.
- After that cleanup, focused Ruff ran once and passed with `All checks passed!`.
- Review 307's targeted acquisition suite had already passed once: 177 tests, exit 0,
  27.333 seconds.
- Review 313's `/tmp` clean-suite result was rejected because it used device 47 instead of
  receipt device 64513.
- Review 314's same-device clean full suite ran once and exited `1` after 2745.672 seconds
  with exactly five unrelated baseline failures and no errors: the missing ignored Uniswap
  pilot fixture DB, the BitMEX six-versus-five symbol expectation, and three EXP-009
  binding-evidence mismatches. Ticket-wide pytest remains non-passing.
- Record 316's same-device repository-wide Ruff passed once in 0.113 seconds, and control
  passed once in 0.068 seconds.

## Final diff-check provenance

The contemporaneous Review 315 execution transcript shows that, after record 316 commit
`029487bac6cfa1435832a6396e130cff613e5233` was pushed, the exact shared-tree command below
was executed once:

```text
git diff --check
```

It exited `0` and produced no output. The transcript does not expose a UTC timestamp for
that direct tool invocation; this record deliberately marks the timestamp as unavailable
rather than fabricating one. The command was not rerun for this correction.

## Preserved accepted evidence

The clean same-device validation used `/home/lars/.cache/tmp/cex002-clean-zyfjn3`, with
repository, cache root, worktree, and receipt device `64513`, and
`PYTHONPATH=/home/lars/.cache/tmp/cex002-clean-zyfjn3/src`. Import resolution was proven
from that clean source tree. The final accepted Gate-2 identities remain:

- acquisition source: `0f8bbf70db167420b5fd5e3b3d0e4d5ed441de580c886909c7bd55426a233981`
- CLI: `6f4b56ecb43dcc448eb6c8cf765e38d9fa3923432459574d913582e3d9c84043`
- test source: `6157fd1f6ba0feccb83965a0ac383985577763edcedc92b0980a4c4cbd499ad6`

The Gate-2 paths remained clean. The shared worktree's unrelated modified and untracked
paths were preserved and were not staged or modified. No validation, source repair, data
mutation, real plan/acquire/verify, or later-ticket work was performed for this correction.
