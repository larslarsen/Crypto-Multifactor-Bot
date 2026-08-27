# CEX-002 Shared-Worktree Failure and Clean Validation

- **Date:** 2026-08-26
- **Reviewer:** Lead Quantitative Finance Researcher/Engineer
- **Ticket:** CEX-002
- **Decision:** focused Ruff accepted; contaminated full-suite result rejected as evidence;
  clean committed-tree validation authorized
- **Authorized actor:** Jr Dev - Hermes
- **Gate 2:** in progress; no real plan or acquisition authorized
- **Next ticket:** `NONE`

## Accepted integration and focused Ruff

Hermes integrated the exact review-311 source and CLI cleanup and pushed commit
`61aada40abe9efe85bd7aa0892413656ef06fb30`. The reviewer verified the integrated Gate-2
paths are clean and retain the accepted identities:

- acquisition source:
  `0f8bbf70db167420b5fd5e3b3d0e4d5ed441de580c886909c7bd55426a233981`;
- CLI: `6f4b56ecb43dcc448eb6c8cf765e38d9fa3923432459574d913582e3d9c84043`;
- test source:
  `6157fd1f6ba0feccb83965a0ac383985577763edcedc92b0980a4c4cbd499ad6`.

The corrected-source focused Ruff command ran exactly once and exited 0 with `All checks
passed!`. This result is accepted. It does not need to run again.

## Shared-worktree full-suite result

The full ticket pytest command then ran exactly once in the preserved shared worktree. It
exited 1 with 20 failures. The first distinct failure was
`tests/acquisition/test_uniswap_v2.py::TestPairCreatedPilotEquivalence::test_existing_receipts_replay_identically_twice`,
which expected 2,120 receipts and observed 3,129.

Hermes correctly stopped before repository-wide Ruff, control, evidence publication, or any
repair. The shared worktree contains substantial uncommitted Uniswap V2 production and test
changes plus other unrelated modified and untracked source. The virtual environment is also an
editable installation whose `.pth` points to the shared worktree's `src`. The full-suite run
therefore exercised uncommitted unrelated code and cannot establish the committed Gate-2
checkpoint's full-suite state. This rejects the run as acceptance evidence without attributing
its 20 failures to CEX-002 or authorizing work on those failures.

## Clean committed-tree validation

Hermes owns one clean offline validation and successful-evidence round. Do not stash, restore,
reset, checkout, clean, stage, modify, or otherwise disturb the shared worktree's unrelated
changes.

Confirm synchronized `HEAD == origin/main` with this review present, integration commit
`61aada40abe9efe85bd7aa0892413656ef06fb30` in its ancestry, the three exact Gate-2 hashes
above, clean Gate-2 paths, and no staged path. Create a new detached Git worktree beneath
`/tmp` at current `HEAD`. Do not reuse an existing path or branch. Inside only that temporary
worktree, create `.venv` as a symlink to `/home/lars/Crypto_Multifactor_Bot/.venv` and export
`PYTHONPATH` as the temporary worktree's absolute `src` directory so the editable-install path
cannot select shared dirty source.

Before validation, run one import-resolution proof which prints the resolved
`cryptofactors.__file__` and fails unless it is beneath the temporary worktree's `src`.
If worktree creation, environment setup, or import proof fails, stop without validation,
repair, cleanup, evidence, commit, or push and report the exact failure.

From the temporary clean worktree, with that `PYTHONPATH` still exported, run the three
remaining ticket commands exactly once in order:

```bash
.venv/bin/python -m pytest tests/ -q --tb=short
.venv/bin/python -m ruff check src/cryptofactors/ scripts/
python3 scripts/check_repo_control.py
```

If any command exits nonzero, stop immediately without repair, rerun, later command, evidence
edit, commit, or push. Return the exact command, exit code, elapsed time, complete summary, and
first distinct failure with its original exception or diagnostic. Leave the detached worktree
for reviewer inspection on failure; do not touch the shared worktree.

If and only if all three commands pass, remove only the newly created detached worktree, using
forced worktree removal if pytest cache or the `.venv` symlink makes it dirty. Return to the
shared worktree and create exactly:

- `research/sprint_004/314_CEX002_GATE2_OFFLINE_VALIDATION_EXECUTION.md`

Record both prior results, the integration commit, detached-worktree commit and path, import
proof, `PYTHONPATH`, each new exact command, start/end UTC timestamps, elapsed time, exit code,
complete pytest/Ruff/control summaries, final Gate-2 hashes, and clean Gate-2 path status.
Explicitly distinguish the rejected shared-dirty result from the clean committed-tree result.

Stage only record 314. Prove the cached path list is exactly that path and run
`git diff --cached --check`. Commit with message
`record CEX-002 Gate-2 offline validation` and push `main`. Then run the ticket's exact
`git diff --check` once in the shared worktree and report its exit code. Do not amend or rerun
if it fails; the pushed evidence commit remains the returned checkpoint.

Stop with the evidence commit, pushed remote, every command result, final hashes, exact clean
status of the three Gate-2 paths, and remaining unrelated shared status. No source/test repair,
real `plan`, `acquire`, or `verify` operation, network access, accepted-data/state mutation,
qualification, sizing, capacity command, Gate 3, normalization, catalog, NautilusTrader,
Harmonic Trader, PAPER/LIVE, or next-ticket work is authorized.

## Reviewer publication scope

The reviewer may stage, commit, and push exactly this review,
`docs/handoff/CURRENT_TASK.md`, and `tickets/CEX-002.md`. Developer source/test paths,
state/data/evidence, and unrelated dirty work are excluded.
