# CEX-002 Hermes Git Sandbox Correction

- **Date:** 2026-08-27
- **Reviewer:** Lead Quantitative Finance Researcher/Engineer
- **Ticket:** CEX-002
- **Decision:** environment-invalid integration attempt rejected; one permission-corrected continuation authorized
- **Authorized actor:** Jr Dev - Hermes
- **Gate 2:** in progress; no raw acquisition fact exists
- **Next ticket:** `NONE`

## Failure review

Hermes completed the review-326 preproof and stopped on the first integration command when Git
reported:

```text
fatal: Unable to create '/home/lars/Crypto_Multifactor_Bot/.git/index.lock': Read-only file system
```

This is a sandbox-permission failure, not a source, test, repository-state, or Git-conflict
failure. The reviewer independently confirmed:

- `HEAD == origin/main == 038d418ef65494ea438753d736fe358c566d36ec`;
- the accepted acquisition source and test remain modified and unstaged;
- the index is empty;
- `.git/index.lock` is absent;
- no integration commit or partial Git mutation exists; and
- focused Ruff and targeted pytest remain unrun.

The accepted review-326 source/test decision is unchanged. Do not recreate, restore, or ask a
source actor to resend the two files.

## Corrected continuation

Hermes must use the execution platform's explicit escalation/approval mechanism for every Git
command that writes `.git`. Do not retry `git add`, `git commit`, or `git push` in the same
read-only sandbox. The permission grant must remain scoped to the exact Git operations in
reviews 326 and 327; it does not authorize filesystem or data mutation outside Git.

Perform only this short continuation:

1. reconfirm synchronized head, the review-326 accepted source/test/CLI hashes, exactly the two
   accepted modified paths among them, an empty index, and absent index lock;
2. with Git write permission, stage only the accepted acquisition source and test;
3. prove the exact cached two-path set and run `git diff --cached --check`;
4. commit with review 326's exact message and push `main`;
5. run review 326's focused Ruff exactly once; and
6. only after Ruff exit 0, run review 326's targeted acquisition pytest exactly once.

Do not rerun the already-passed full preproof or any unspent command more than once. Any failed
predicate, denied escalation, Git failure, nonzero validation result, or timeout stops without
repair, rerun, later command, or evidence edit.

Only after both validations pass, publish review 326's exact evidence as renumbered record:

- `research/sprint_004/328_CEX002_RETAINED_AUTHORITY_INTEGRATION_AND_VALIDATION.md`

Stage/commit/push only record 328 using approved Git writes, run final shared-tree
`git diff --check` once, and stop. Do not touch the rejected real Gate-2 store.

Full-suite pytest, repository-wide Ruff, control, retirement, corrected planning, acquisition,
replay, `verify`, qualification, sizing, capacity, network/data mutation, Gate 3,
normalization, catalog, NautilusTrader, Harmonic Trader, experiments, PAPER/LIVE, and
next-ticket work remain unauthorized. Gate 2 remains `IN_PROGRESS`; next ticket remains
`NONE`.

## Reviewer publication scope

The reviewer may stage, commit, and push exactly this review,
`docs/handoff/CURRENT_TASK.md`, and `tickets/CEX-002.md`. Developer source/test paths,
ignored state/data, and unrelated dirty work are excluded.
