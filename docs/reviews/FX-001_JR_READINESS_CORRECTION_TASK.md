# FX-001 - JR READINESS CORRECTION TASK

**Ticket:** `tickets/FX-001.md`
**Actor:** Jr Dev - Hermes
**Status:** COMPLETED
**Next ticket:** `NONE`

## Assignment

Correct `docs/reviews/FX-001_READINESS_REPORT.md` under REVIEW-0080.

## Required Corrections

- Cite the implemented REF `FIAT`/`STABLE` classes, instrument base/quote IDs, generic dataset
  manifest/publisher, and SQLite data-plane exclusion. Distinguish capability from actual seeded or
  registered USD/stablecoin identities.
- Replace the source matrix with exact audited statuses and citations. Use “not audited/not
  accepted for FX” where evidence is absent; do not infer categorical provider incapability,
  licensing, historical depth, availability time, or revision behavior.
- Provide one exact proposed Parquet observation schema table with field name, physical/logical
  type, nullability, unit, semantic invariant, and identity participation. Eliminate every “or.”
- Define the canonical observation identity body, decimal precision/scale, UTC representation,
  dataset type, schema/transform versions, canonical row order, partition path, manifest
  dependencies, and deterministic report schema.
- Separate observation time, source publication time, system acquisition time, and availability
  time. Specify fail-closed depeg, stale, missing, revision, disagreement, and as-of join policies
  without silently introducing fills or haircuts.
- State whether existing generic catalog metadata is sufficient. Recommend a SQL migration only for
  a concrete control-plane invariant that generic manifests cannot express; never store FX rows in
  SQLite.
- Give an ordered ticket split with exact inputs, outputs, boundaries, acceptance tests, and exact
  commands for each proposed phase.
- Select exactly one smallest next action: source-feasibility audit, ADR, or implementation block.
  Because no FX source is accepted, any implementation recommendation must remain blocked until
  source authority is established.

## Constraints

Records and repository analysis only. No source, tests, migrations, ADRs, provider calls, generated
data, or architecture edits.

## Records And Publication

Update the readiness report, ticket, README, backlog, handoff, and task/review statuses. Run
repository control, commit and push the records, set `AWAITING_REVIEW`, name Reviewer as next actor,
and retain `Next ticket authorized: NONE`.

## Completion Condition

The published corrected report supports one reviewer decision without inventing source facts or
persistence contracts.
