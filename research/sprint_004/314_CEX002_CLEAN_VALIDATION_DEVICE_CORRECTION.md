# CEX-002 Clean Validation Device Correction

- **Date:** 2026-08-26
- **Reviewer:** Lead Quantitative Finance Researcher/Engineer
- **Ticket:** CEX-002
- **Decision:** wrong-device clean validation rejected; same-device clean validation authorized
- **Authorized actor:** Jr Dev - Hermes
- **Gate 2:** in progress; no real plan or acquisition authorized
- **Next ticket:** `NONE`

## Accepted stop

Hermes completed review 313 preproof and setup, created detached worktree
`/tmp/cex002-clean-gISLup`, bound `PYTHONPATH` to its `src`, and proved imports resolved from
that clean tree. The full suite then ran exactly once from
`2026-08-27T02:32:27.505801255Z` through `2026-08-27T03:17:22.723131010Z`. It exited 1 after
2,695.218 seconds with 5 failures and 13 errors. The first distinct error was:

```text
AttestationError: receipt 258 is stored on a different device than it declares
```

Hermes correctly stopped before Ruff, control, cleanup, evidence, repair, commit, or push.

## Device diagnosis

Review 313 incorrectly required the clean worktree beneath `/tmp`. The reviewer independently
measured:

| Path | Device |
|---|---:|
| `/home/lars/Crypto_Multifactor_Bot` | 64513 |
| accepted receipt 258 | 64513 |
| `/home/lars/.cache/tmp` | 64513 |
| `/tmp` | 47 |
| `/tmp/cex002-clean-gISLup` | 47 |

Receipt 258 declares `dev:64513`, and the capacity-attestation source deliberately rejects a
receipt file on another device. The review-313 worktree location therefore made the clean test
environment invalid before CEX-002 semantics could be evaluated. This result is rejected as
acceptance evidence and does not authorize a source/test repair.

## Corrected same-device validation

Hermes must first remove only the failed detached worktree
`/tmp/cex002-clean-gISLup` through Git worktree removal; forced removal is authorized only for
that exact temporary path. Do not remove or alter any other worktree.

Confirm synchronized `HEAD == origin/main` with this review present, integration commit
`61aada40abe9efe85bd7aa0892413656ef06fb30` in its ancestry, the three review-313 Gate-2
hashes, clean Gate-2 paths, and no staged path. Prove `/home/lars/.cache/tmp`, the repository,
and accepted receipt 258 all have numeric device 64513 before creating a unique new detached
worktree under `/home/lars/.cache/tmp` at current `HEAD`. Prove the new worktree and its copy of
receipt 258 also have device 64513.

Inside only that new worktree, create `.venv` as a symlink to the shared `.venv`, export
`PYTHONPATH` as the new worktree's absolute `src`, and repeat review 313's import-resolution
proof. If cleanup, preproof, worktree creation, device proof, environment setup, or import proof
fails, stop without validation, repair, evidence, commit, or push and report the exact failure.

From the new same-device clean worktree, with its clean `PYTHONPATH` still exported, run these
commands exactly once in order:

```bash
.venv/bin/python -m pytest tests/ -q --tb=short
.venv/bin/python -m ruff check src/cryptofactors/ scripts/
python3 scripts/check_repo_control.py
```

If any command exits nonzero, stop immediately without repair, rerun, later command, evidence
edit, commit, push, or temporary-worktree removal. Return the exact command, exit code, elapsed
time, complete summary, and first distinct failure with its original exception or diagnostic.

If and only if all three commands pass, remove only the newly created clean worktree, return to
the shared worktree, and create exactly:

- `research/sprint_004/315_CEX002_GATE2_OFFLINE_VALIDATION_EXECUTION.md`

Use review 313's complete evidence contract, additionally recording both device-invalid and
same-device clean runs plus every device proof. Stage only record 315, prove that cached path
and run `git diff --cached --check`, commit with message
`record CEX-002 Gate-2 offline validation`, and push `main`. Then run the ticket's exact
`git diff --check` once in the shared worktree and report its exit code. Do not amend or rerun
if it fails.

Stop with the evidence commit, pushed remote, every command result, final hashes, exact clean
Gate-2 status, and remaining unrelated shared status. No source/test repair, real `plan`,
`acquire`, or `verify` operation, network access, accepted-data/state mutation, qualification,
sizing, capacity command, Gate 3, normalization, catalog, NautilusTrader, Harmonic Trader,
PAPER/LIVE, or next-ticket work is authorized.

## Reviewer publication scope

The reviewer may stage, commit, and push exactly this review,
`docs/handoff/CURRENT_TASK.md`, and `tickets/CEX-002.md`. Developer source/test paths,
state/data/evidence, and unrelated dirty work are excluded.
