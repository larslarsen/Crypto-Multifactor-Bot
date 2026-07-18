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
- Do not start the next ticket until the current one is accepted.
- When told "do not modify or recommit", obey strictly.
- When a senior engineer says files must be created, create them in a focused commit.
- Use `git push origin HEAD:main` when instructed to surface a commit.
- Verify with `git rev-parse origin/main` after push.

## Enforcement

A governance control script (`scripts/check_repo_control.py`) is run as part of reviews. It validates presence of key artifacts (this file, active ticket, current ADRs, etc.).

