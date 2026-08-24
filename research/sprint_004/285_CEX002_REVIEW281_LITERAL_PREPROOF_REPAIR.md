# CEX-002 Review-281 Literal Preproof Repair

- **Date:** 2026-08-23
- **Reviewer:** Lead Quantitative Finance Researcher/Engineer
- **Ticket:** CEX-002
- **Decision:** repair review 281's literal preproof clause
- **Authorized actor:** Jr Dev - Hermes
- **Gate 2:** not accepted; review-281 execution pending
- **Next ticket:** `NONE`

Hermes correctly reported that correction 284 did not alter review 281's literal
`HEAD == ee3f9d7` sentence and stopped again. Review 281 itself is now corrected to require
only synchronized `HEAD == origin/main` plus review-281 commit `15a03cb` as an ancestor.
It explicitly prohibits an exact `HEAD` requirement because every committed reviewer
control correction advances the branch.

The corrected review-281 SHA-256 is
`e6a3f5c432ec3a9a7419507168802c1f31d7a5e74adc6871f96e221b42969d5d`.
Correction 284 and current task are updated to that identity. All accepted implementation
hashes, commands, output 282, record 283, Git scope, stop rules, and prohibitions remain
unchanged. Hermes must execute review 281 now and stop for reviewer inspection.

The reviewer may stage, commit, and push exactly:

- `research/sprint_004/281_CEX002_CAPACITY_ATTESTATION_SOURCE_ACCEPTANCE_AND_EXECUTION.md`;
- `research/sprint_004/284_CEX002_REVIEW281_BASE_PREPROOF_CORRECTION.md`;
- this repair;
- `docs/handoff/CURRENT_TASK.md`; and
- `tickets/CEX-002.md`.

Developer source/test paths, attestation evidence, execution record, and unrelated dirty
work are excluded. Gate 2 remains not accepted and next ticket remains `NONE`.
