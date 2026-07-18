# ADR-0008 — Research, Paper, and Live artifact promotion lifecycle

**Status:** Proposed
**Date:** 2026-07-18
**Amends:** ADR-0006 (Typed artifact promotion and serving parity)

## Decision

We adopt an explicit three-stage lifecycle for every promotable research artifact:

```text
Research → Paper → Live
```

Each stage is an authorization boundary, not a performance milestone. Promotion is an
explicit, recorded event carrying the exact artifact identity and the authorizing
authority. This ADR clarifies promotion and serving authorization. It does **not** change
the Data, Research, or Execution layer boundaries established by RFC-001 / ADR-0001–0007.

The Evidence Registry and the Promotion Registry are distinct systems:

- The **Evidence Registry** records *scientific* verdicts (`SUPPORTED`, `REPLICATED`,
  `REJECTED`, `QUARANTINED`, …). A verdict is a judgment about evidence, not a permission
  to serve or spend capital.
- The **Promotion Registry** records *operational / capital* authorization (the stage an
  artifact may occupy and whether it may serve paper or live). Promotion state is decided
  by an explicit promotion event, never inferred from an Evidence Registry verdict.

A hypothesis reaching `SUPPORTED` or `REPLICATED` does **not** create a paper or live
promotion. Promotion requires its own event and its own gates.

## Lifecycle stages

### Research

- Experiments and portfolio simulations occur here.
- Outputs are immutable experiment bundles and candidate artifacts.
- Research artifacts have **no** serving authorization.
- Scientific acceptance requires preregistered, reproducible, point-in-time-correct,
  costed evidence.

### Paper

- Only a specifically promoted immutable artifact may enter paper serving.
- Paper operation must use the same features, transformations, representation,
  configuration, and portfolio logic approved in research.
- Paper evaluation covers serving parity, data freshness, deterministic decisions,
  execution simulation, accounting reconciliation, operational stability, and drift.
- Paper approval does **not** authorize live capital.

### Live

- Live use requires a separate, explicit owner-authorized promotion event.
- Authorization identifies the exact artifact, configuration, universe, risk limits,
  execution routes, and effective interval.
- A new artifact version does **not** inherit the prior version's live authorization.
- Suspension, rollback, retirement, and emergency disablement are append-only events.

## Promotion states

The Promotion Registry uses an explicit state vocabulary:

- `RESEARCH_CANDIDATE`
- `RESEARCH_ACCEPTED`
- `PAPER_APPROVED`
- `PAPER_SUSPENDED`
- `LIVE_APPROVED`
- `LIVE_SUSPENDED`
- `RETIRED`
- `REJECTED`
- `QUARANTINED`

`REJECTED` and `QUARANTINED` are terminal-for-promotion outcomes (an artifact may not be
promoted from them without a new artifact identity). `PAPER_SUSPENDED` and `LIVE_SUSPENDED`
are reversible append-only events, not deletions. `RETIRED` is permanent for that identity.

Scientific verdicts (Evidence Registry) and promotion states (Promotion Registry) are
kept separate so that a strong evidence result cannot silently become a serving or capital
authorization, and so that a promotion decision is always traceable to a specific event
and authority.

## Immutable identity

Every promotion event must identify the exact:

- artifact or model-manifest ID;
- experiment fingerprint;
- dataset and universe IDs;
- code and configuration versions;
- feature and representation versions;
- portfolio and cost-model versions;
- risk-policy version;
- promotion target (Paper / Live);
- effective time;
- approving authority;
- evidence snapshot or review reference.

Any material modification creates a new artifact identity that starts in Research. Serving
must never discover artifacts by filenames, directory recency, or a `latest` convention
(this restates and hardens ADR-0006).

## Gates

### Research → Paper

Require at minimum:

- accepted scientific review;
- immutable experiment bundle;
- valid point-in-time and causal integrity;
- costed portfolio acceptance;
- complete lineage;
- research/serving parity test;
- deterministic replay;
- compatible model manifest;
- explicit paper promotion event.

### Paper → Live

Require at minimum:

- a minimum prospective paper observation requirement declared **before** review;
- accounting and position reconciliation;
- stable data and feature operation;
- acceptable realized versus modeled costs;
- no unresolved critical incidents;
- risk-limit and kill-switch verification;
- owner approval;
- explicit live promotion event.

The minimum prospective paper observation requirement and any performance thresholds are
**policy parameters** that must be specified before each candidate's paper evaluation
begins. This ADR does **not** define an automatic time period or a performance threshold;
doing so would prejudge a candidate before its evaluation plan exists.

## Consequences

- ADR-0006's typed-promotion and serving-parity rules are preserved and made explicit as a
  state machine.
- The Evidence Registry scope is narrowed to scientific verdicts; serving/capital
  authorization moves to the Promotion Registry.
- `schemas/model_manifest.schema.json` `promotion_status` enum is widened to the nine
  canonical states.
- `research/sprint_001/sql/control_schema.sql` (proposal) `model_promotion_event` and
  `model_artifact` are extended with the immutable-identity columns and a `promotion_state`
  enum.
- Implementation of the Promotion Registry and its state machine is deferred to a dedicated
  ticket (`PROMO-001`), which stays blocked until research, serving, and execution
  foundations exist.
- No production Python, broker, paper-execution, or runtime-promotion code is introduced by
  this ADR.

## Status and authority

This ADR is **Proposed**. Per ADR-0011 / the repository control plane, junior-created ADRs
are not marked Accepted unless the owner has authorized direct acceptance. Acceptance and
any resulting implementation authorization are the owner's decision.
