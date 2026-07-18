# PROMO-001 — Implement the Promotion Registry and state machine

**Priority:** P1
**Status:** BLOCKED
**Dependencies:** research foundations (RFC-001 / ADR-0001–0007), serving foundations
(`serving` domain), execution foundations (paper/live execution), ADR-0008
**Layer:** catalog / promotion (new)
**Architecture change:** none (implements ADR-0008)

> **Control-plane note:** This ticket is **not** the active task. `GOV-001` remains the
> active ticket. This ticket is blocked and must not be started, authorized, or promoted
> to active until the owner explicitly authorizes it. It must not replace GOV-001 and must
> not authorize new implementation work on its own.

## Objective

Implement the Promotion Registry and its explicit state machine described in ADR-0008,
turning the `model_promotion_event` / `model_artifact` proposal schema into enforced,
append-only runtime behavior.

## Scope

- Enforce the nine promotion states: `RESEARCH_CANDIDATE`, `RESEARCH_ACCEPTED`,
  `PAPER_APPROVED`, `PAPER_SUSPENDED`, `LIVE_APPROVED`, `LIVE_SUSPENDED`, `RETIRED`,
  `REJECTED`, `QUARANTINED`.
- Validate the immutable-identity payload on every promotion event (artifact/manifest ID,
  experiment fingerprint, dataset + universe IDs, code/config versions, feature +
  representation versions, portfolio + cost-model versions, risk-policy version, target,
  effective time, approving authority, evidence reference).
- Enforce the Research→Paper and Paper→Live gates from ADR-0008 (no auto time period or
  performance threshold).
- Keep the Evidence Registry and Promotion Registry distinct: an Evidence Registry verdict
  never creates a promotion.
- Serving discovery must use manifest/state identity, never filenames, directory recency,
  or a `latest` convention.

## Out of scope (this ticket)

- No live execution, broker code, or order routing.
- No paper-execution runtime (paper simulation belongs to the serving/execution foundation).
- No new factor or model research.

## Blocking prerequisites (must exist before this ticket is authorized)

- `catalog` migration runner (CAT-001 / CAT-001A) available to apply the schema.
- `experiments` domain producing immutable experiment bundles + fingerprints.
- `serving` domain able to read promotion state and fail closed.
- `portfolio` domain exposing portfolio/cost-model versions for lineage.
- Owner-declared policy parameters for each candidate's paper evaluation (prospective
  observation requirement, risk limits, kill-switch verification procedure).

## Acceptance (draft; refine when unblocked)

- Deterministic, forward-only migrations for the promotion tables.
- A promotion event with a missing identity field is rejected.
- A `PAPER_APPROVED` event without an accepted scientific review reference is rejected.
- A `LIVE_APPROVED` event without owner authority is rejected.
- A new artifact version starts in `RESEARCH_CANDIDATE` (does not inherit prior authorization).
- Suspension / retirement / rejection events are append-only and never mutate history.
- Focused tests using temporary databases.

## Stop condition

Implement only what this ticket asks for. Stop and report. Do not begin downstream
execution tickets.
