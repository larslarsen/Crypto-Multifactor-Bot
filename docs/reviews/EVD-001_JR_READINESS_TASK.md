# EVD-001 - JR READINESS AUDIT

**Ticket:** `tickets/EVD-001.md`
**Actor:** Jr Dev - Hermes
**Status:** AUTHORIZED - RECORDS/ANALYSIS ONLY
**Next ticket:** `NONE`

## Objective

Resolve the ticket's undefined `experiment identity contract` dependency and convert its broad
deliverables into a reviewable implementation contract before any production source is written.

## Required inspection

Jr must inspect the existing experiment schema, migration `0002_evidence_registry.sql`, migration
framework, `research/evidence/hypotheses.yaml`, current package/CLI conventions, and relevant
architecture/layer rules.

## Required report

Create `docs/reviews/EVD-001_READINESS_REPORT.md` containing:

1. The authoritative experiment/hypothesis identity and versioning rules already present in the
   repository, plus any unresolved dependency.
2. The exact migration-0002 tables, constraints, and invariants available to the implementation.
3. A proposed minimal module/API and CLI surface matching repository conventions.
4. Deterministic hash, append-only decision, snapshot, export, and seed-import contracts.
5. A concrete acceptance-test matrix and exact ordered acceptance commands.
6. Layer/import boundaries, excluded scope, security risks, and a recommendation to authorize or
   block Sr production-source work.

## Constraints

- No production source, tests, migrations, schemas, architecture decisions, or research content.
- Do not infer missing contracts; identify them explicitly for reviewer decision.
- Update EVD-001 activation/status records, run repository control, commit and push the records,
  set `AWAITING_REVIEW` with reviewer next, and stop.
