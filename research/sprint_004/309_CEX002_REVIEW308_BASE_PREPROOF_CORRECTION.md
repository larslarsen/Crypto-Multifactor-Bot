# CEX-002 Review-308 Base Preproof Correction

- **Date:** 2026-08-26
- **Reviewer:** Lead Quantitative Finance Researcher/Engineer
- **Ticket:** CEX-002
- **Decision:** incorrect expanded integration SHA corrected; offline authorization resumed
- **Authorized actor:** Jr Dev - Hermes
- **Gate 2:** in progress; no real plan or acquisition authorized
- **Next ticket:** `NONE`

## Preproof failure accepted

Hermes stopped review 308 before every validation command because the review supplied the
invalid full commit name `cee2b8a82e88ed31e3b99d640ded569632494f00`. Hermes performed no
source change, staging, commit, push, validation command, or `git diff --check`. That stop was
correct and is accepted.

The reviewer had expanded the valid abbreviated integration commit incorrectly. The actual
repository identity is:

```text
cee2b8a3c2c3693818c2fd34ec5016465e6be9cb correct CEX-002 Gate-2 recovery regressions
```

The reviewer verified that exact commit exists and is an ancestor of the review-308
publication. This is a governance-identity correction only. It changes no source, test,
test result, acceptance decision, or engineering contract.

## Corrected Hermes authorization

Review 308 remains authoritative except for these two literal replacements:

1. Every occurrence of the invalid full integration SHA is replaced by
   `cee2b8a3c2c3693818c2fd34ec5016465e6be9cb`.
2. The successful execution record reserved as record 309 is renamed to exactly
   `research/sprint_004/310_CEX002_GATE2_OFFLINE_VALIDATION_EXECUTION.md`, because this
   correction occupies record 309.

Hermes must begin a fresh preproof. Establish synchronized `HEAD == origin/main` with this
correction present, prove exact integration commit
`cee2b8a3c2c3693818c2fd34ec5016465e6be9cb` is an ancestor, prove the three review-308 hashes
and clean Gate-2 path status, and prove no staged path. Then execute the complete review-308
four-command sequence exactly once in order under its original stop rules.

If all four commands pass, create, stage, commit, and push only record 310 under review 308's
evidence contract and commit message `record CEX-002 Gate-2 offline validation`. Then execute
the exact final `git diff --check` once and stop with the required return. If any command
fails, stop exactly as review 308 requires.

No source repair, additional command, real `plan`, `acquire`, or `verify` operation, network
access, data/state mutation, qualification, sizing, capacity command, Gate 3, normalization,
catalog, NautilusTrader, Harmonic Trader, PAPER/LIVE, or next-ticket work is authorized.

## Reviewer publication scope

The reviewer may stage, commit, and push exactly this correction,
`docs/handoff/CURRENT_TASK.md`, and `tickets/CEX-002.md`. Published review 308, developer
source/test paths, state/data/evidence, and unrelated dirty work are excluded.
