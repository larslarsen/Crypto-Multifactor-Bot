# Development Roles and Minimum-Capable-Usage Policy

This document records the development roles and the routing policy for assigning
engineering work in this repository. It is governance/documentation only; it changes
no code, migrations, tickets, or acceptance state.

## Roles

- **Lead Quantitative Finance Researcher/Engineer (reviewer):** inspects commits, makes
  engineering decisions, accepts or rejects work, selects the minimum-usage capable
  developer, and authorizes the next ticket.
- **Sr Dev — Hermes:** agentic, using `grok-build-0.1`. Default owner of senior
  production-source implementation and correction work. No tests, integration,
  repository records, Git, commits, or pushes.
- **Sr Dev — Grok Build:** agentic, using Grok 4.5. Escalation-only option for difficult
  concurrency, bitemporal logic, architecture, cross-module reasoning, or failed Sr Dev —
  Hermes work. No tests, integration, repository records, Git, commits, or pushes.
- **Jr Dev — Hermes:** agentic, using Tencent `hy3:free`. Owns source-drop integration,
  test creation and execution, repository records, Git, commits, and pushes.
- **Owner:** relays one-way prompts and supplies repository URLs, hashes, ZIPs, and
  source drops.

## Routing order

1. **Jr Dev — Hermes** for integration, testing, records, and Git duties.
2. **Sr Dev — Hermes** as the default senior production coder.
3. **Sr Dev — Grok Build** only when the difficulty or prior failure justifies higher
   usage.
4. **Grok.com Auto or Expert chat modes** are optional external reasoning surfaces, not
   formal developer roles; their underlying models and usage rates must not be assumed.

## Routing principle

Routing prioritizes the **cheapest capable agent**, engineering risk, user effort, and
observed results. Do not hard-code unverified subscription-cost ratios; the order above
reflects capability tiers and escalation need, not assumed price differences.

## Removed role

**Sr Dev — Sandbox** is no longer a formal role in this repository's governance. Its prior
source-edits-only responsibilities are consolidated under **Sr Dev — Hermes** (default
senior coder). References to Sr Dev — Sandbox in other documents are superseded by this
policy.
