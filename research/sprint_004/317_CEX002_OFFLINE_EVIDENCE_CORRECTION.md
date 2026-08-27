# CEX-002 Offline Evidence Correction

- **Date:** 2026-08-27
- **Reviewer:** Lead Quantitative Finance Researcher/Engineer
- **Ticket:** CEX-002
- **Decision:** Ruff/control results accepted; execution record incomplete and correction required
- **Authorized actor:** Jr Dev - Hermes
- **Gate 2:** in progress; no real plan or acquisition authorized
- **Next ticket:** `NONE`

## Accepted results

Hermes published record 316 alone in pushed commit
`029487bac6cfa1435832a6396e130cff613e5233`. The reviewer verified the record, commit,
clean Gate-2 paths, and unchanged identities.

The clean same-device repository-wide Ruff command is accepted: exit 0 in 0.113 seconds with
`All checks passed!`. The immediately following clean control command is accepted: exit 0 in
0.068 seconds with `Repo control check: PASS`. The worktree was removed and unrelated shared
changes were preserved.

## Evidence defects

Record 316 is not accepted as the complete offline execution record because:

1. it says review 308 focused Ruff passed, but review 308's focused Ruff exited 1 with three
   unused-binding findings; the corrected focused Ruff passed only after Spark cleanup and
   integration under review 311;
2. it omits the required cleanup integration commit
   `61aada40abe9efe85bd7aa0892413656ef06fb30`; and
3. neither record 316 nor the relayed completion states whether the review-315 post-push exact
   `git diff --check` ran or what its result was.

These are evidence defects, not authority for source/test work or command repetition.

## Hermes evidence-only correction

Hermes must not rerun pytest, focused Ruff, repository-wide Ruff, control, import/device proof,
or any other completed command.

First consult the contemporaneous review-315 execution/session transcript without running a
repository command. If the exact post-push `git diff --check` already ran after commit
`029487bac6cfa1435832a6396e130cff613e5233`, do not rerun it; preserve and report its exact
timestamp, exit code, and output. If the transcript proves it did not run, execute that exact
command once now in the shared worktree and record its timestamp, exit code, and complete
output. If its status cannot be established, stop without command or edit and report the
ambiguity.

Once the result is established, create exactly:

- `research/sprint_004/318_CEX002_GATE2_OFFLINE_VALIDATION_EXECUTION_CORRECTION.md`

Do not modify record 316. Record 318 must explicitly correct the three defects above, identify
record-316 commit `029487bac6cfa1435832a6396e130cff613e5233`, preserve every accepted command
result and exact five unrelated full-suite blockers, and state that ticket-wide pytest remains
non-passing. Include the final `git diff --check` provenance and exact result.

Stage only record 318. Prove the cached path list is exactly that path and run
`git diff --cached --check`. Commit with message
`correct CEX-002 Gate-2 offline validation evidence` and push `main`. Stop with the evidence
commit, pushed remote, record hash/length, clean Gate-2 status, and remaining unrelated status.

No source/test repair, validation rerun, real `plan`, `acquire`, or `verify` operation, network
access, accepted-data/state mutation, Gate 3, normalization, catalog, NautilusTrader, Harmonic
Trader, PAPER/LIVE, or next-ticket work is authorized.

## Reviewer publication scope

The reviewer may stage, commit, and push exactly this review,
`docs/handoff/CURRENT_TASK.md`, and `tickets/CEX-002.md`. Developer source/test paths,
state/data/evidence, and unrelated dirty work are excluded.
