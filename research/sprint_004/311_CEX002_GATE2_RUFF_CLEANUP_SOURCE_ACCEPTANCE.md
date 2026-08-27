# CEX-002 Gate-2 Ruff Cleanup Source Acceptance

- **Date:** 2026-08-26
- **Reviewer:** Lead Quantitative Finance Researcher/Engineer
- **Ticket:** CEX-002
- **Decision:** exact mechanical cleanup accepted for integration and offline validation
- **Authorized actor:** Jr Dev - Hermes
- **Gate 2:** in progress; no real plan or acquisition authorized
- **Next ticket:** `NONE`

## Inspected Spark return

The reviewer inspected the complete two-file Spark return once:

- `src/cryptofactors/acquisition/binance_usdm_harmonic_acquisition.py`:
  `0f8bbf70db167420b5fd5e3b3d0e4d5ed441de580c886909c7bd55426a233981`,
  10,521 lines;
- `scripts/research/acquire_binance_usdm_harmonic_release.py`:
  `6f4b56ecb43dcc448eb6c8cf765e38d9fa3923432459574d913582e3d9c84043`,
  150 lines; and
- unchanged `tests/acquisition/test_binance_usdm_harmonic_acquisition.py`:
  `6157fd1f6ba0feccb83965a0ac383985577763edcedc92b0980a4c4cbd499ad6`,
  4,897 lines and 177 test functions.

The diff contains exactly review 310's three deletions: the unused CLI
`EXIT_UNSAFE_STATE` import, `replace` from the production module's dataclass import, and the
unused `content_inode` assignment. The CLI's required `from dataclasses import replace`
remains. No test or other path changed. Spark supplied no command result, and the reviewer ran
no test or acceptance command.

This mechanical cleanup is accepted. It changes no acquisition, recovery, receipt,
validation, or exit behavior.

## Hermes integration and consolidated validation

Hermes owns one integration, offline validation, and successful-evidence publication round.
Do not alter source, tests, CLI, ticket, handoff, ADR, existing evidence, data, or unrelated
dirty work.

Preproof must establish synchronized `HEAD == origin/main` with this review present, the three
exact hashes above, clean test status, only the source and CLI modified among Gate-2 paths, and
no staged path.

Stage exactly the source and CLI. Prove the cached path list contains only those two paths and
run `git diff --cached --check`. Commit with message
`remove CEX-002 Gate-2 Ruff dead code` and push `main`.

After that checkpoint push, run these four commands exactly once in order. This is a fresh
validation of the corrected source state. If any command exits nonzero, stop immediately
without repair, rerun, later command, evidence edit, commit, or push. Return the exact command,
exit code, elapsed time, complete summary, and first distinct failure with its original
exception or diagnostic.

```bash
.venv/bin/python -m ruff check src/cryptofactors/acquisition/binance_usdm_harmonic_acquisition.py scripts/research/acquire_binance_usdm_harmonic_release.py tests/acquisition/test_binance_usdm_harmonic_acquisition.py
.venv/bin/python -m pytest tests/ -q --tb=short
.venv/bin/python -m ruff check src/cryptofactors/ scripts/
python3 scripts/check_repo_control.py
```

If and only if all four commands pass, create exactly:

- `research/sprint_004/312_CEX002_GATE2_OFFLINE_VALIDATION_EXECUTION.md`

Record the review-308 targeted 177-test pass, review-310 focused Ruff failure and stop, cleanup
integration commit, preproof, each new exact command, start/end UTC timestamps, elapsed time,
exit code, complete pytest summary, complete Ruff/control summaries, final three hashes, and
clean Gate-2 path status. Record that full-suite and repository-wide validation ran in the
preserved shared worktree with unrelated dirty paths present; do not stage or modify them.

Stage only record 312. Prove the cached path list is exactly that path and run
`git diff --cached --check`. Commit with message
`record CEX-002 Gate-2 offline validation` and push `main`. Then run the ticket's exact
`git diff --check` once and report its exit code. Do not amend or rerun if it fails; the
already-pushed evidence commit remains the returned checkpoint.

Stop with both commits, pushed remote, every command result, final hashes, exact clean status
of the three Gate-2 paths, and remaining unrelated status. No real `plan`, `acquire`, or
`verify` operation, network access, data/state mutation, qualification, sizing, capacity
command, Gate 3, normalization, catalog, NautilusTrader, Harmonic Trader, PAPER/LIVE, or
next-ticket work is authorized.

## Reviewer publication scope

The reviewer may stage, commit, and push exactly this review,
`docs/handoff/CURRENT_TASK.md`, and `tickets/CEX-002.md`. Developer source/test paths,
state/data/evidence, and unrelated dirty work are excluded.
