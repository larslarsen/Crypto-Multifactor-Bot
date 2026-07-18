# Workflow

This document describes the day-to-day control plane for the Crypto Multifactor Bot
repository. It is the operational companion to ADR-0011.

## Principles

- The repository is the single source of truth.
- Exactly one ticket is active at a time.
- Development agents commit locally and stop.
- The **owner** (or a designated reviewer) publishes commits and accepts work.
- Chat instructions are not durable state until recorded in the repository.

## Roles

### Development agent (junior)

- Reads `docs/handoff/CURRENT_TASK.md` to find the single active ticket.
- Reads the ticket in `tickets/` and implements only what it asks for.
- Writes or updates tests first where practical; implements the smallest change that
  satisfies the ticket.
- Runs the ticket's acceptance commands (and `scripts/check_repo_control.py` for
  governance tickets).
- Commits locally in a focused commit with a concise message.
- Stops. Does **not** push, inspect remotes, or verify public GitHub state.

### Owner / designated reviewer

- Publishes commits to the reviewed branch (e.g. `main`).
- Accepts a ticket by recording `**Status:** ACCEPTED` (or a review document) in the
  repository.
- Authorizes the next ticket by updating `docs/handoff/CURRENT_TASK.md` and setting
  `Next ticket authorized` to a complete ticket ID.
- Is the only party that decides ticket progression.

## Active ticket format

`docs/handoff/CURRENT_TASK.md` uses a fixed field format:

```text
Ticket: GOV-001
State: AWAITING_REVIEW
Governing documents:
- docs/adr/0011-repo-governance-and-agent-instructions.md
- docs/reviews/REVIEW-0003_GOV-001.md
Authorized scope: Complete GOV-001 only.
Required outcome: GOV-001 acceptance checks pass.
Stop condition: Commit and stop for review.
Next ticket authorized: NONE
```

### State values

`DRAFT`, `READY`, `IN_PROGRESS`, `BLOCKED`, `AWAITING_REVIEW`, `ACCEPTED`,
`SUPERSEDED`.

### Rules enforced by the validator

- Exactly one `Ticket:` field.
- The ticket file must exist under `tickets/`.
- The task `State:` must be valid.
- The ticket's `**Status:**` must match the current-task state.
- Every document listed under `Governing documents:` must exist.
- `Next ticket authorized` is `NONE` or a complete ticket ID (digits).
- When `State` is `BLOCKED` or `AWAITING_REVIEW`, next must be `NONE`.
- No governance doc hard-codes a ticket assignment.
- No governance doc requires development agents to push or verify remotes.

## Ticket lifecycle

```text
DRAFT -> READY -> IN_PROGRESS -> AWAITING_REVIEW -> ACCEPTED
                         |                         |
                         v                         v
                      BLOCKED ---------------> SUPERSEDED (if superseded)
```

- `BLOCKED` work must have `Next ticket authorized: NONE` until unblocked.
- `AWAITING_REVIEW` work must have `Next ticket authorized: NONE` until accepted.
- Only the owner/reviewer moves a ticket to `ACCEPTED` and authorizes the next one.

## Review documents

Reviews live in `docs/reviews/` and are named `REVIEW-NNNN_<TICKET>.md`. A review
records the decision and the date. Acceptance is recorded by the reviewer, not the
development agent.

## Change reports

Each ticket that changes code or behavior includes a change report
(`docs/reviews/<TICKET>_CHANGE_REPORT.md`) stating files changed, design choices,
commands run with real results, acceptance criteria demonstrated, and unresolved
risks.

## Stop condition

After the acceptance commands pass, the development agent commits locally and stops.
It does not start the next ticket, push, or verify remotes. Progression is the
owner's/reviewer's decision.
