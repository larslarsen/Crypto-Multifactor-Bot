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
- Do not start the next ticket until the current one is accepted by the Lead
  Quantitative Finance Researcher/Engineer (reviewer) and the next ticket is
  authorized. Acceptance and next-ticket authorization are exclusive to the reviewer;
  the owner is the prompt relay only and is not an acceptance authority.
- The repository has three governance actors (reviewer, senior coder, relay owner)
  plus the Jr Dev integration role:
  - **Lead Quantitative Finance Researcher/Engineer (reviewer):** inspects commits, makes
    engineering decisions, accepts or rejects work, selects the minimum-usage capable
    developer, and authorizes the next ticket.
  - **Sr Dev — Grok Build:** agentic, using Grok 4.5. Sole formal senior production-code
    role: owns senior code reasoning and source edits only. No tests, integration,
    repository records, Git, commits, or pushes.
  - **Jr Dev — Hermes:** agentic, using the best reliable free Nous Portal model currently
    available. Owns source-drop integration, test creation/execution, repository records,
    Git, commits, and pushes.
  - **Owner:** relays one-way prompts and supplies repository URLs, hashes, ZIPs, and
    source drops.
- Routing is based on end-to-end accepted-result quality, engineering risk, and
  reliability — not nominal per-token price. See `docs/engineering/DEVELOPMENT_ROLES.md`.
- The owner relays the reviewer's one-way developer prompts. Developers do not chat
  with the reviewer.
- **Reviewer acceptance is exclusive.** Only the Senior Quantitative Finance
  Researcher/Engineer accepts or rejects engineering work and authorizes the next
  ticket. The owner is the prompt relay only and is not an alternate acceptance
  authority. Publication (commit + push) is Hermes's duty, not a gated owner-only
  action.

## Enforcement

A governance control script (`scripts/check_repo_control.py`) is run as part of reviews.
It validates the repository-native control plane: exactly one active ticket, a matching
ticket status and current-task state, the existence of referenced governing documents,
and the `NONE` next-ticket rule for blocked / awaiting-review work.

