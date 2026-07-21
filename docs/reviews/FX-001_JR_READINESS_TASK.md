# FX-001 - JR READINESS TASK

**Ticket:** `tickets/FX-001.md`
**Actor:** Jr Dev - Hermes
**Status:** COMPLETED - READINESS ACCEPTED BY REVIEW-0081
**Next ticket:** `NONE`

## Assignment

Create `docs/reviews/FX-001_READINESS_REPORT.md` from repository evidence.

## Required Inspection

- Stablecoin-FX requirements in architecture, risk, resource, source-plan, universe, and validation
  documents.
- Accepted reference-master, canonical-bar, manifest, raw-object, catalog, and dataset-publisher
  contracts and layer-import rules.
- Current SQL migrations and whether any stablecoin-FX/control identity already exists.
- Sprint-003 source decisions, especially Binance, Bybit, Coin Metrics, DefiLlama stablecoin data,
  provider revision behavior, and point-in-time availability limitations.
- Existing stablecoin exclusion/classification evidence in research and reference data.

## Required Report

The report must provide:

1. Exact repository facts and contradictions; distinguish implemented contracts from proposals.
2. A source-authority matrix covering historical depth, observation time, availability time,
   revisions, raw capture, licensing, and accepted/deferred status.
3. Proposed minimal typed observation/dataset identity and deterministic Parquet/report schema.
4. Point-in-time policies for depegs, stale/missing data, fills, source disagreement, quarantine,
   and fail-closed downstream conversion.
5. Integration boundaries with reference assets/instruments, canonical bars, manifests, catalog,
   and downstream universe/labels.
6. Whether an ADR, SQL migration, new source audit, or architecture clarification is required.
7. A concrete implementation split, acceptance-test matrix, exact gate commands, and explicit
   excluded scope.
8. A recommendation to authorize a smallest source task or keep FX-001 blocked.

## Constraints

No production source, tests, migrations, ADRs, provider calls, generated data, research conclusions,
or architecture edits. Do not infer absent source or identity contracts; record them as blockers.

## Records And Publication

Update ticket, README, implementation backlog, and handoff for the readiness state. Run repository
control, commit and push the review/task/report records, then set `AWAITING_REVIEW`, name Reviewer as
next actor, and retain `Next ticket authorized: NONE`.

## Completion Condition

The published repository contains a source-grounded readiness report and returns control to
Reviewer without authorizing implementation.
