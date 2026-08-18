# Development Roles and Minimum-Capable-Usage Policy

This document records the development roles and the routing policy for assigning
engineering work in this repository. It is governance/documentation only; it changes
no code, migrations, tickets, or acceptance state.

## Roles

- **Lead Quantitative Finance Researcher/Engineer (reviewer):** inspects commits, makes
  engineering decisions, accepts or rejects work, selects the minimum-usage capable
  developer, and authorizes the next ticket.
- **Implementation Dev — Codex Spark:** agentic, using GPT-5.3-Codex-Spark High.
  Authors reviewer-bounded low/medium-risk boilerplate, scaffolding, mechanical adapters,
  schema plumbing, CLI wiring, and their test source. It does not make architecture,
  financial-semantics, source-authority, concurrency, or transaction-design decisions.
  It does not execute tests or own integration, repository records, Git, commits, or
  pushes.
- **Sr Dev — Grok Build:** agentic, using Grok 4.6 High. The sole formal senior
  production-code role. Owns senior code reasoning and architecture-sensitive,
  financial-semantic, source-authority, concurrency, transaction, or corrective source
  and test-source creation. Does not execute tests or own integration, repository
  records, Git, commits, or pushes.
- **Jr Dev — Hermes:** agentic, using the best reliable free Nous Portal model currently
  available. Owns production/test source-drop integration, test and acceptance-command
  execution, repository records, Git, commits, and pushes. Does not design or author tests.
- **Owner:** relays one-way prompts and supplies repository hashes, ZIPs, URLs, and
  source drops.

## Routing order

1. **Jr Dev — Hermes** for integration, test execution, records, and Git duties.
2. **Implementation Dev — Codex Spark** for bounded boilerplate and mechanical source
   work where the reviewer has already fixed the design and semantics.
3. **Sr Dev — Grok Build** for senior design-sensitive work, correction after semantic or
   authority failure, and review-hard source where accepted-result risk dominates usage.
4. **Sr Dev — Grok Build escalation tiers** (or an alternate capable senior agent) only
   when the difficulty or prior failure justifies higher usage.

## Routing principle

Model and developer selection are based on **end-to-end usage per accepted result**,
engineering risk, and reliability — not nominal per-token price. A cheaper source author
is not selected when ambiguity or correction risk is likely to consume more review and
integration usage than it saves. Do not hard-code a specific promotional Nous model;
free availability may rotate. Ordinary Grok chat is an external reasoning surface, not a
formal development role in this policy.

## Removed roles

**Sr Dev — Hermes** and **Sr Dev — Sandbox** are no longer formal roles in this
repository's governance. Their prior source/test-authoring responsibilities are routed
between **Implementation Dev — Codex Spark** and **Sr Dev — Grok Build** under the risk
boundary above. References to Sr Dev — Hermes or Sr Dev — Sandbox in other documents are
superseded by this policy.
