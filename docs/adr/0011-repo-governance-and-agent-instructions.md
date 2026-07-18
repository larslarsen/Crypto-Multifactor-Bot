# ADR 0011 — Repository governance via tickets, ADRs, and agent instructions

- **Status:** Accepted
- **Date:** 2026-07-18

## Decision

We adopt an explicit governance layer on top of the frozen architecture:

- All work is driven by numbered tickets in `tickets/`.
- Architecture and cross-cutting decisions are recorded in `docs/adr/`.
- AI agents and human contributors are instructed via a root `AGENTS.md`.
- A lightweight control script (`scripts/check_repo_control.py`) validates the presence of key governance artifacts.
- The current task is always declared in `docs/handoff/CURRENT_TASK.md`.
- Changes are only considered visible for review once they appear on public `origin/main`.

## Rationale

- Makes the repo self-driving and reviewable by seniors without constant context transfer.
- Prevents drift between what agents are told and what is actually on main.
- Provides a clear stopping point ("stop for review") per ticket.
- Aligns with the existing Evidence Registry, ADR process, and layer boundaries.

## Enforcement

- The control script is run as part of acceptance for governance and future meta-tickets.
- Reviewers are expected to look at `git rev-parse origin/main` and the files on that tree.
- Agents are instructed not to claim a commit is ready until it is visible on public main.

## Consequences

- Slight extra overhead on every piece of work (ticket + possible ADR).
- Forces explicit communication when the senior engineer wants changes surfaced.
- Reduces "Hermes did X but it's not on GitHub yet" situations.

