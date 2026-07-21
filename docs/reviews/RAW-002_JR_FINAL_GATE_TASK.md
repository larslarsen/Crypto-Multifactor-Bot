# RAW-002 - JR FINAL TEST AND GATE TASK

**Ticket:** `tickets/RAW-002.md`
**Actor:** Jr Dev - Hermes
**Status:** COMPLETED
**Next ticket:** `NONE`

## Assignment

Resolve REVIEW-0076 without changing production source.

## Required Work

- Correct the parent-symlink fixture so the outside target contains the exact object at the path
  reached after following the substituted symlink. Either replace the `ab` directory and create
  `<outside>/<cd>/<hash>`, or replace the `cd` directory and create `<outside>/<hash>`.
- Keep exact expected bytes and size, and assert `_sha256_file` is not called.
- Run all six commands from `docs/reviews/RAW-002_JR_INTEGRATION_TASK.md` verbatim, with no broader,
  narrower, reordered, or substituted commands.
- Record each exact command and outcome. Never label a failing command as passed.
- Correct the change report, handoff, ticket, README, backlog, and task status consistently.

## Records And Publication

If every exact gate passes, set the ticket and handoff to `AWAITING_REVIEW`, name Reviewer as next
actor, retain `Next ticket authorized: NONE`, commit, and push. If any gate fails, set both to
`BLOCKED`, record the exact failure, retain `Next ticket authorized: NONE`, commit, and push.

## Completion Condition

The published repository contains a valid parent-symlink exploit fixture and truthful evidence from
all six exact gates.
