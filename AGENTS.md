# AGENTS.md

This file governs how AI agents (and humans acting as agents) work in this repository.

## Core Rules

- The repository is the single source of truth.
- All changes must be traceable to a ticket in `tickets/`.
- Architecture changes require an ADR in `docs/adr/`.
- Evidence, hypotheses, experiments, and decisions live in `research/`.
- Never bypass the layer boundaries defined in the architecture.
- Do not hard-code secrets or network credentials.
- Prefer deterministic, reviewable changes over clever one-liners.

## Ticket Workflow

1. Read the current task from `docs/handoff/CURRENT_TASK.md`.
2. Read the full ticket in `tickets/`.
3. Implement only what the ticket asks for.
4. Run the acceptance commands listed in the ticket.
5. Update the change report if required.
6. Stop when the ticket says to stop for review.

## Agent Behavior

- Be literal. Answer the question that was asked.
- Work on exactly one active ticket at a time.
- Do not start the next ticket until the current one is accepted by the owner or a
  designated reviewer.
- The owner publishes commits. Development agents commit locally and stop; they do not
  push, inspect remotes, or verify public GitHub state.
- When told "do not modify or recommit", obey strictly.
- When a senior engineer says files must be created, create them in a focused commit.
- Chat instructions are not durable state until they are recorded in the repository
  (a ticket, ADR, or control document).
- The owner is the acceptance and publication authority only. The owner does not act as a
  relay or messenger between agents and other stakeholders (seniors, reviewers). Seniors and
  reviewers prompt the agent directly; the agent executes and stops for the owner's review.
  Do not draft relay/prompt blocks for the owner to forward on the owner's behalf.

## Enforcement

A governance control script (`scripts/check_repo_control.py`) is run as part of reviews.
It validates the repository-native control plane: exactly one active ticket, a matching
ticket status and current-task state, the existence of referenced governing documents,
and the `NONE` next-ticket rule for blocked / awaiting-review work.

