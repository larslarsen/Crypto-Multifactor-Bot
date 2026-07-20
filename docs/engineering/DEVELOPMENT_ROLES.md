# Development Roles and Minimum-Capable-Usage Policy

This document records the development roles and the routing policy for assigning
engineering work in this repository. It is governance/documentation only; it changes
no code, migrations, tickets, or acceptance state.

## Roles

- **Lead Quantitative Finance Researcher/Engineer (reviewer):** inspects commits, makes
  engineering decisions, accepts or rejects work, selects the minimum-usage capable
  developer, and authorizes the next ticket.
- **Sr Dev — Grok Build:** agentic, using Grok 4.5. The sole formal senior
  production-code role. Owns senior code reasoning and source edits only. No tests,
  integration, repository records, Git, commits, or pushes.
- **Jr Dev — Hermes:** agentic, using the best reliable free Nous Portal model currently
  available. Owns source-drop integration, test creation and execution, repository
  records, Git, commits, and pushes.
- **Owner:** relays one-way prompts and supplies repository hashes, ZIPs, URLs, and
  source drops.

## Routing order

1. **Jr Dev — Hermes** for integration, testing, records, and Git duties.
2. **Sr Dev — Grok Build** as the default senior production coder.
3. **Sr Dev — Grok Build escalation tiers** (or an alternate capable senior agent) only
   when the difficulty or prior failure justifies higher usage.

## Routing principle

Model and developer selection are based on **end-to-end usage per accepted result**,
engineering risk, and reliability — not nominal per-token price. The order above
reflects capability tiers and escalation need. Do not hard-code a specific promotional
Nous model; free availability may rotate. Ordinary Grok chat is an external reasoning
surface, not a formal development role in this policy.

## Removed roles

**Sr Dev — Hermes** and **Sr Dev — Sandbox** are no longer formal roles in this
repository's governance. Their prior source-edits-only responsibilities are consolidated
under **Sr Dev — Grok Build** (sole senior coder). References to Sr Dev — Hermes or Sr
Dev — Sandbox in other documents are superseded by this policy.
