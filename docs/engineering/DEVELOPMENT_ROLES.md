# Development Roles and Minimum-Capable-Usage Policy

This document records the development roles and the routing policy for assigning
engineering work in this repository. It is governance/documentation only; it changes
no code, migrations, tickets, or acceptance state.

## Roles

- **Lead Quantitative Finance Researcher/Engineer (reviewer):** inspects commits, makes
  engineering decisions, accepts or rejects work, selects the minimum-usage capable
  developer, and authorizes the next ticket. May directly stage, commit, and push a small
  reviewer-authored governance/review publication whose exact paths are enumerated in the
  active review. This exception excludes developer source/test integration,
  acceptance-suite or acceptance-command execution, implementation evidence, and data
  mutation. At the owner's explicit direction, the reviewer may run one enumerated
  targeted test command against an unintegrated developer drop solely for immediate
  source-review feedback. The result does not integrate or accept the drop and does not
  transfer Hermes's validation, evidence, records, or Git ownership.
- **Implementation Dev — Codex Spark:** agentic, using GPT-5.3-Codex-Spark High.
  Authors reviewer-bounded low/medium-risk boilerplate, scaffolding, mechanical adapters,
  schema plumbing, CLI wiring, and their test source. It does not make architecture,
  financial-semantics, source-authority, concurrency, or transaction-design decisions.
  It does not execute tests or own integration, repository records, Git, commits, or
  pushes.
- **Sr Dev — Grok Build:** agentic, using Grok 4.6 High. A formal senior production-code
  actor. Owns senior code reasoning and architecture-sensitive,
  financial-semantic, source-authority, concurrency, transaction, or corrective source
  and test-source creation. Does not execute tests or own integration, repository
  records, Git, commits, or pushes.
- **Sr Dev — Claude Build:** agentic, using Claude Opus 5. An alternate formal senior
  production-code actor with the same senior source/test-source ownership and the same
  prohibition on test execution, integration, records, and Git. Only one senior actor is
  authorized for each bounded drop.
- **Sr Dev — Codex Sol:** agentic, using GPT-5.6-sol High. An alternate formal senior
  production-code actor with the same senior source/test-source ownership and the same
  prohibition on test execution, integration, records, and Git. The reviewer may select it
  when task fit, repeated rejection, actor availability, or remaining usage justifies the
  route. Only one senior actor is authorized for each bounded drop.
- **Targeted senior test exception:** for a bounded corrective drop, the reviewer may
  explicitly authorize the selected senior actor to run one enumerated targeted test
  command against the actor's edited path
  when immediate source feedback reduces integration handoffs. This narrow exception does
  not transfer integration, acceptance-suite, repository-record, Git, commit, push, data,
  or publication ownership. The senior stops on the first nonzero result and reports the
  exact command and output.
- **Jr Dev — Hermes:** agentic, using the best reliable free Nous Portal model currently
  available. Owns production/test source-drop integration, test and acceptance-command
  execution, implementation/evidence records, and the corresponding Git, commits, and
  pushes. Does not design or author tests. The reviewer may publish only the narrow
  governance/review exception above.
- **Owner:** relays one-way prompts and supplies repository hashes, ZIPs, URLs, and
  source drops.

## Routing order

1. **Reviewer** for small exact-path reviewer-authored governance/review publications;
   **Jr Dev — Hermes** for integration, test execution, implementation/evidence records,
   and their Git duties.
2. **Implementation Dev — Codex Spark** for bounded boilerplate and mechanical source
   work where the reviewer has already fixed the design and semantics.
3. **Sr Dev — Grok Build, Sr Dev — Claude Build, or Sr Dev — Codex Sol**, selected
   explicitly by the reviewer, for senior design-sensitive work, correction after semantic
   or authority failure, and review-hard source where accepted-result risk dominates usage.
4. A higher reasoning tier or alternate senior is used only when task difficulty, repeated
   rejection, availability, or remaining usage justifies it.

## Routing principle

Model and developer selection are based on **end-to-end usage per accepted result**,
engineering risk, and reliability — not nominal per-token price. A cheaper source author
is not selected when ambiguity or correction risk is likely to consume more review and
integration usage than it saves. Do not hard-code a specific promotional Nous model;
free availability may rotate. Ordinary Grok chat is an external reasoning surface, not a
formal development role in this policy.

Grok, Claude, and Codex Sol are not routed by a permanent brand preference or by exhausting
one quota before using another. The reviewer uses repository-specific evidence: first-pass
source acceptance, number and severity of review corrections, control-plane adherence,
total usage through accepted integration, availability, remaining quota, and fit to the
bounded task. When a senior actor repeats a semantic miss, the next bounded correction
should normally rotate when another senior is available so the project gains comparative
evidence instead of paying for the same failure mode again. CEX-002 review 64 is the first
such Claude Build authorization; Review 357 adds the first availability-driven Codex Sol
authorization.

## Removed roles

**Sr Dev — Hermes** and **Sr Dev — Sandbox** are no longer formal roles in this
repository's governance. Their prior source/test-authoring responsibilities are routed
between **Implementation Dev — Codex Spark** and the reviewer-selected formal senior
actor under the risk boundary above. References to Sr Dev — Hermes or Sr Dev — Sandbox in
other documents are superseded by this policy.
