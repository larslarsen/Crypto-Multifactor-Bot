# ADR 0011 — Repository governance via tickets, ADRs, and agent instructions

- **Status:** Accepted
- **Date:** 2026-07-18

## Decision

We adopt an explicit governance layer on top of the frozen architecture:

- All work is driven by numbered tickets in `tickets/`.
- Architecture and cross-cutting decisions are recorded in `docs/adr/`.
- AI agents and human contributors are instructed via a root `AGENTS.md`.
- A dependency-free control script (`scripts/check_repo_control.py`) validates the
  repository-native control plane (exactly one active ticket, matching status/state,
  referenced governing documents, and the `NONE` next-ticket rule for blocked /
  awaiting-review work).
- The current task is always declared in `docs/handoff/CURRENT_TASK.md` using a fixed
  field format.
- The repository uses a **control plane**, not an autonomous workflow:
  - there is no self-driving or autonomous ticket progression;
  - development agents do **not** push, inspect remotes, or verify public GitHub state;
  - the **owner** publishes commits;
  - there is **exactly one** active ticket at a time;
  - development agents commit locally and stop;
  - only the owner or a designated reviewer accepts work or authorizes the next ticket;
  - chat instructions are not durable state until recorded in the repository.

## Rationale

- Makes the repo reviewable by the owner/senior without constant context transfer.
- Prevents drift between what agents are told and what is actually on `main`.
- Provides a clear stopping point ("stop for review") per ticket.
- Keeps the publishing step with the owner, so review authority is explicit and the
  agent never has to reason about remote or CI state.
- Aligns with the existing Evidence Registry, ADR process, and layer boundaries.

## Enforcement

- The control script is run as part of acceptance for governance and future meta-tickets.
- Reviewers inspect the files on the reviewed commit/tree directly.
- Agents are instructed to commit locally and stop; they must not push or verify remotes.
- A ticket is only accepted, or its next ticket authorized, by the owner or designated
  reviewer recording that decision in the repository.

## Consequences

- Slight extra overhead on every piece of work (ticket + possible ADR).
- Forces explicit communication when the owner wants changes surfaced.
- Reduces "the agent did X but it isn't on the reviewed tree yet" ambiguity, because the
  agent stops and the owner controls publication.
