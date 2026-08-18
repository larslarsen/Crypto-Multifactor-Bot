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
  plus the implementation and Jr Dev integration roles:
  - **Lead Quantitative Finance Researcher/Engineer (reviewer):** inspects commits, makes
    engineering decisions, accepts or rejects work, selects the minimum-usage capable
    developer, and authorizes the next ticket. To avoid a separate integration handoff,
    the reviewer may directly stage, commit, and push a small reviewer-authored
    governance/review publication when its exact paths are enumerated in the active
    review. This exception never includes developer source/test integration, test or
    acceptance-command execution, or data mutation.
  - **Implementation Dev — Codex Spark:** agentic, using GPT-5.3-Codex-Spark High.
    Authors reviewer-bounded low/medium-risk boilerplate, scaffolding, mechanical adapters,
    and their test source. It does not make architecture, financial-semantics, source-
    authority, concurrency, or transaction-design decisions. It does not execute tests or
    own integration, repository records, Git, commits, or pushes.
  - **Sr Dev — Grok Build:** agentic, using Grok 4.6 High. A formal senior production-code
    actor for architecture-sensitive, financial-semantic, source-authority, concurrency,
    transaction, or corrective source and test-source creation. Does not execute tests or
    own integration, repository records, Git, commits, or pushes.
  - **Sr Dev — Claude Build:** agentic, using Claude Opus 5. An alternate formal senior
    production-code actor with the same source/test-source scope and prohibitions as Grok
    Build. The reviewer authorizes exactly one senior actor for a bounded drop based on
    accepted-result evidence, remaining usage, and task fit; the roles are not concurrent.
  - **Jr Dev — Hermes:** agentic, using the best reliable free Nous Portal model currently
    available. Owns production/test source-drop integration, test and acceptance-command
    execution, implementation/evidence records, and the corresponding Git, commits, and
    pushes. Does not design or author tests. Small reviewer-authored governance/review
    publications may instead be published directly by the reviewer under the exception
    above.
  - **Owner:** relays one-way prompts and supplies repository URLs, hashes, ZIPs, and
    source drops.
- Routing is based on end-to-end accepted-result quality, engineering risk, and
  reliability — not nominal per-token price. See `docs/engineering/DEVELOPMENT_ROLES.md`.
- The owner relays the reviewer's one-way developer prompts. Developers do not chat
  with the reviewer.
- **Reviewer acceptance is exclusive.** Only the Senior Quantitative Finance
  Researcher/Engineer accepts or rejects engineering work and authorizes the next
  ticket. The owner is the prompt relay only and is not an alternate acceptance
  authority. Implementation/evidence publication remains Hermes's duty; narrowly scoped
  reviewer-authored governance/review publication may be performed by the reviewer and is
  never a gated owner-only action.

## Archive

Historical tickets and intermediate review records have been moved to `~/cmb_archive/`.
Agents must not read, search, or reference files in `~/cmb_archive/`. The archive is
excluded from the agent search path. All active work lives in the repo tree.

## Enforcement

A governance control script (`scripts/check_repo_control.py`) is run as part of reviews.
It validates the repository-native control plane: exactly one active ticket, a matching
ticket status and current-task state, the existence of referenced governing documents,
and the `NONE` next-ticket rule for blocked / awaiting-review work.
