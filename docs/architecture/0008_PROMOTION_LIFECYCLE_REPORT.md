# Architecture-change report — ADR-0008 Research/Paper/Live promotion lifecycle

**Date:** 2026-07-18
**ADR:** docs/architecture/adr/0008-research-paper-live-promotion-lifecycle.md
**Status of ADR:** Proposed (owner acceptance pending)
**Author:** junior developer (Hermes)
**Ticket:** PROMO-001 (blocked; not active; does not replace GOV-001)

## What was missing from the existing design

The v1 architecture froze in RFC-001 with ADR-0006 ("Typed artifact promotion and serving
parity") covering the *mechanism* of promotion (explicit record + typed manifest, no
filename discovery). But it did not define:

- an explicit three-stage lifecycle (`Research → Paper → Live`) as distinct authorization
  boundaries;
- a canonical promotion-state vocabulary (the `model_manifest.schema.json` enum was
  incomplete: `QUARANTINED_LEGACY`, `RESEARCH_ONLY`, `PAPER_APPROVED`, `LIVE_APPROVED`,
  `RETIRED`);
- the exact immutable identity that every promotion event must pin;
- the Research→Paper and Paper→Live gate sets;
- the hard separation between Evidence Registry *scientific verdicts* and Promotion
  Registry *serving/capital authorization*.

The system-architecture diagram (§3) collapsed promotion into a single "Promotion
registry → Paper serving; later live serving" node with no rejected/quarantined/suspended/
retired side paths.

## How Research, Paper, and Live now differ

- **Research** is where experiments and portfolio simulations happen. Outputs are immutable
  bundles and candidate artifacts. No serving authorization exists here.
- **Paper** requires an explicit promotion of one immutable artifact; it must reuse the
  exact features, transforms, representation, config, and portfolio logic approved in
  research. Paper approval is *not* live capital authorization.
- **Live** requires a *separate*, explicit, owner-authorized promotion event that pins the
  exact artifact, configuration, universe, risk limits, execution routes, and effective
  interval. A new artifact version does not inherit a prior version's live authorization.

## Why Evidence Registry verdicts and Promotion Registry authorization are separate

A scientific verdict answers "what did we learn, and is it supported?" A promotion state
answers "is this exact artifact allowed to serve paper or live capital, by whose
authority?" Conflating them lets a `SUPPORTED`/`REPLICATED` hypothesis silently become a
serving or capital authorization, which violates point-in-time discipline and removes the
explicit owner decision required for live use. Keeping them separate means promotion is
always an explicit, recorded event traceable to a specific authority and evidence
reference, and a strong evidence result cannot move capital on its own.

## Files changed

Architecture / governance:
- `docs/architecture/adr/0008-research-paper-live-promotion-lifecycle.md` — new ADR (Proposed).
- `docs/architecture/adr/README.md` — registered ADR-0008 (amends 0006).
- `docs/architecture/00_SYSTEM_ARCHITECTURE.md` — §3 diagram now shows the explicit
  Research→Paper→Live flow with rejected/quarantined/suspended/retired side paths; added
  "Artifact promotion lifecycle (see ADR-0008)" note.
- `docs/architecture/12_EVIDENCE_REGISTRY.md` — clarified it supplies evidence/verdicts
  only and does not grant serving/capital authorization.

Schemas / proposals:
- `schemas/model_manifest.schema.json` — `promotion_status` enum widened to the nine
  canonical states (replacing the incomplete prior enum).
- `research/sprint_001/sql/control_schema.sql` (proposal) — `model_artifact.status` and
  `model_promotion_event` extended with the canonical `promotion_state` CHECK and the
  immutable-identity columns (fingerprint, dataset/universe IDs, code/config/feature/
  representation/portfolio/cost-model/risk-policy versions, effective time, approving
  authority, evidence reference); action set widened to PROMOTE/SUSPEND/RESUME/RETIRE/
  REJECT/QUARANTINE.

Tickets / reports:
- `tickets/PROMO-001.md` — new blocked future-implementation ticket (not active).
- `docs/architecture/0008_PROMOTION_LIFECYCLE_REPORT.md` — this report.

No production Python, broker, paper-execution, or runtime-promotion code was changed or
added (consistent with the task scope).

## What future implementation is required

- `PROMO-001` — implement the Promotion Registry and state machine against the extended
  schema. It stays BLOCKED until research, serving, and execution foundations exist.
- A schema migration for `model_artifact` / `model_promotion_event` once `catalog` (CAT-001/
  CAT-001A) is the applied baseline.
- Serving-side enforcement: `serving` must read promotion state and fail closed; no
  filename / `latest` discovery.

## Unresolved policy parameters

These are deliberately **not** fixed by this ADR; they are policy parameters that must be
specified before each candidate's paper evaluation begins:

- the minimum **prospective paper observation requirement** (declared before review);
- risk limits and kill-switch verification procedure for live promotion;
- acceptable realized-vs-modeled cost tolerance;
- any performance threshold the owner chooses to apply (none is imposed by this ADR).

## Consistency / verification

- `scripts/check_repo_control.py` remains PASS: `CURRENT_TASK.md` (GOV-001) and the
  governance docs were not altered in a way that affects the active-ticket check; GOV-001
  stays the active ticket.
- No runtime code changed, so no unit/lint/type checks are impacted by this task.
- The `model_manifest.schema.json` edit is a forward-compatible enum widening; existing
  `additionalProperties: false` is preserved.
- The `control_schema.sql` change is a proposal DDL edit; it is not executed by any current
  runtime.

## Stop condition

Documentation/schema consistency complete. One focused local commit made. Not pushed
(owner publishes). GOV-001 remains the active ticket; PROMO-001 is blocked and not
authorized.
