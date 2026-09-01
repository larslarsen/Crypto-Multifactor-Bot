# CEX-002 Review 441 — Hermes Terminal Watch Authorization

- **Date:** 2026-09-01
- **Reviewer:** Lead Quantitative Finance Researcher/Engineer
- **Ticket:** CEX-002
- **Decision:** delegate the sole existing conversion watch to Jr Dev — Hermes
- **Gate 2:** `ACCEPTED`
- **Gate 3:** `IN_PROGRESS`
- **Next required actor:** Jr Dev — Hermes
- **Next ticket:** `NONE`

The owner explicitly requested that Hermes, not the paid reviewer and not Sol, babysit the running
conversion. Review 440 proved that the sole Review-437 process remains live in the Hermes execution
environment and advances shared output after the harness returns. Manual reviewer polling is
stopped.

Hermes now performs one persistent continuation. It reads AGENTS.md, CURRENT_TASK, CEX-002, Review
440, and this authorization; confirms that no Review-439 runner exists; confirms the exact
Review-437 shell/Python identities and accepted command; and remains attached only as a read-only
watcher until that existing Python process reaches a terminal state. It must not return merely
because the process is still live. It may poll without signaling or modifying the process.

There is no launch, retry, replacement, signal, cleanup, patch, test, acquisition, or second
runner. On terminal success Hermes performs the full Review-437 reconciliation. On terminal
failure it records complete evidence without reproduction or retry. It then publishes
`research/sprint_004/442_CEX002_OPEN_INTEREST_TERMINAL_RECORD.md`, updates CURRENT_TASK and the
ticket with both actor fields returned to the reviewer, stages exactly those three paths, commits,
pushes, proves `HEAD == origin/main`, and stops.

Under the AGENTS.md reviewer governance-publication exception this authorization commits and
pushes exactly this file, `docs/handoff/CURRENT_TASK.md`, and `tickets/CEX-002.md`. All data,
implementation, runner, wrapper, and unrelated dirty paths remain unstaged and untouched.
