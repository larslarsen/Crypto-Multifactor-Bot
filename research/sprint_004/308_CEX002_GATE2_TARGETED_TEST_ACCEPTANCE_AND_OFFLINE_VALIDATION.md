# CEX-002 Gate-2 Targeted Test Acceptance and Offline Validation

- **Date:** 2026-08-26
- **Reviewer:** Lead Quantitative Finance Researcher/Engineer
- **Ticket:** CEX-002
- **Decision:** targeted Gate-2 suite accepted; consolidated offline validation authorized
- **Authorized actor:** Jr Dev - Hermes
- **Gate 2:** in progress; no real plan or acquisition authorized
- **Next ticket:** `NONE`

## Accepted integration and targeted result

Hermes integrated the review-307 correction and pushed commit
`cee2b8a82e88ed31e3b99d640ded569632494f00`. The reviewer verified
`HEAD == origin/main == cee2b8a82e88ed31e3b99d640ded569632494f00`, the three Gate-2 paths
are clean, and their identities are:

- `src/cryptofactors/acquisition/binance_usdm_harmonic_acquisition.py`:
  `9476ccff836542509efe7e5169f0cb9d10d40a831fde0153415a4a667ff97065`
- `scripts/research/acquire_binance_usdm_harmonic_release.py`:
  `bb6038559d45bddfb011925ad96eb9552cbe4b71bfd5051375adbdcd3de555a9`
- `tests/acquisition/test_binance_usdm_harmonic_acquisition.py`:
  `6157fd1f6ba0feccb83965a0ac383985577763edcedc92b0980a4c4cbd499ad6`

The exact review-307 targeted pytest command ran once from
`2026-08-26T23:47:54.106542354Z` through `2026-08-26T23:48:21.435360032Z`. It
completed in 27.333 seconds with exit 0 and all 177 tests passed. The one emitted ZIP
duplicate-name warning is an expected synthetic duplicate-member boundary exercised by the
test suite and is not a failure.

This accepts the integrated source and targeted test result. It does not accept Gate 2 and
does not authorize a real plan, acquisition, or verifier run.

## Reviewer command-scope note

While inspecting the dirty shared worktree, the reviewer inadvertently included read-only
`git diff --check` in a status command. It exited 0 and changed no file or Git state, but it
was outside the reviewer's acceptance-command scope. That result is excluded from acceptance
evidence. Hermes must execute the authorized command below; the reviewer invocation does not
satisfy it.

## Consolidated Hermes authorization

Hermes owns one offline validation and evidence-publication round. Do not alter any source,
test, CLI, ticket, handoff, ADR, existing evidence, data, or unrelated dirty path.

Preproof must establish:

- synchronized `HEAD == origin/main` with this review present and integration commit
  `cee2b8a82e88ed31e3b99d640ded569632494f00` in its ancestry;
- the three exact Gate-2 hashes above;
- clean status for those three paths; and
- no staged path.

Run the following commands exactly once in this order. If any command exits nonzero, stop
immediately without repair, rerun, later command, evidence edit, commit, or push. Return the
exact command, exit code, elapsed time, complete summary, and first distinct failure with its
original exception or diagnostic.

```bash
.venv/bin/python -m ruff check src/cryptofactors/acquisition/binance_usdm_harmonic_acquisition.py scripts/research/acquire_binance_usdm_harmonic_release.py tests/acquisition/test_binance_usdm_harmonic_acquisition.py
.venv/bin/python -m pytest tests/ -q --tb=short
.venv/bin/python -m ruff check src/cryptofactors/ scripts/
python3 scripts/check_repo_control.py
```

If and only if all four commands pass, create exactly:

- `research/sprint_004/309_CEX002_GATE2_OFFLINE_VALIDATION_EXECUTION.md`

Record the preproof, each exact command, start/end UTC timestamps, elapsed time, exit code,
complete pytest summary, complete Ruff/control summaries, the three final hashes, and the
fact that the Gate-2 paths remained clean. Record that the full-suite and repository-wide
results were obtained in the preserved shared worktree with unrelated dirty paths present;
do not stage or modify those paths.

Stage only record 309. Prove the cached path list is exactly that path and run
`git diff --cached --check`. Commit with message
`record CEX-002 Gate-2 offline validation` and push `main`. Then run the ticket's exact
`git diff --check` command once and report its exit code. Do not amend or rerun if it fails;
the already-pushed evidence commit remains the returned checkpoint.

Stop with the evidence commit, pushed remote, command results, final hashes, exact clean
status of the three Gate-2 paths, and the remaining unrelated status. No real `plan`,
`acquire`, or `verify` operation, network access, data/state mutation, qualification, sizing,
capacity command, Gate 3, normalization, catalog, NautilusTrader, Harmonic Trader,
PAPER/LIVE, or next-ticket work is authorized.

## Reviewer publication scope

The reviewer may stage, commit, and push exactly this review,
`docs/handoff/CURRENT_TASK.md`, and `tickets/CEX-002.md`. Developer source/test paths,
state/data/evidence, and unrelated dirty work are excluded.
