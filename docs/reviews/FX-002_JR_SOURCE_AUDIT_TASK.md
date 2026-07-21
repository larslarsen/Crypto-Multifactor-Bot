# FX-002 - JR SOURCE FEASIBILITY AUDIT TASK

**Ticket:** `tickets/FX-002.md`
**Actor:** Jr Dev - Hermes
**Status:** COMPLETED
**Next ticket:** `NONE`

## Assignment

Create `docs/reviews/FX-002_SOURCE_FEASIBILITY_REPORT.md` and supporting evidence under
`research/fx_002/`.

## Audit Requirements

- Use only repository-known candidate providers listed in `tickets/FX-002.md` and official/public
  endpoints or downloads. Do not use credentials or add a new provider silently.
- Capture bounded raw responses/files outside Git, compute SHA-256, and record request identity,
  retrieval time, provider timestamp fields, coverage, pagination, response headers relevant to
  availability/revision, licensing evidence, and local evidence path.
- Test direct USD-per-stablecoin market observations. Define direction as USD received per one unit
  of stablecoin. Record inversion explicitly if a provider publishes the reciprocal.
- Include bounded observations spanning at least one known depeg interval when the source claims
  sufficient history; a source that only returns current values cannot qualify as historical PIT.
- Distinguish observation time, provider publication time, retrieval time, and the earliest
  defensible availability time. Unknown publication/availability semantics must fail the PIT gate.
- Determine revision behavior using checksums, version/vintage support, replacement policy, or a
  documented absence of such evidence. Current API output must never be treated as a historical
  vintage without proof.
- Treat stablecoin/stablecoin exchange pairs only as secondary cross-checks, never as an independent
  USD anchor.

## Required Artifacts

- `docs/reviews/FX-002_SOURCE_FEASIBILITY_REPORT.md`
- `research/fx_002/EVIDENCE_REGISTER.csv` with stable evidence IDs, URLs/requests, retrieval UTC,
  SHA-256, byte size, storage location, and licensing/status fields
- one source note per evaluated provider under `research/fx_002/sources/`
- a deterministic decision matrix covering historical depth, direct USD anchor, timestamps,
  availability, revisions, raw reproducibility, licensing, rate direction, depeg coverage, and
  accepted/deferred/rejected status

Raw provider payloads remain outside Git; commit only hashes, metadata, bounded safe excerpts where
licensing permits, and analytical records.

## Decision Rule

Recommend exactly one primary source only if all PIT, raw-lineage, direction, revision, licensing,
and depeg-observation gates pass. Otherwise recommend `NONE` and state the precise blocker. Do not
recommend implementation conditionally on invented assumptions.

## Exact Acceptance Commands

1. `python3 scripts/check_repo_control.py`
2. `PYTHONPATH=src uv run pytest -q --tb=short`

Record exact outputs. No production source, tests, migrations, schemas, ADRs, or architecture edits
are authorized by this audit task.

## Records And Publication

Mark FX-001 accepted/closed under REVIEW-0081. Update FX-002, README, backlog, and handoff. After
publishing the audit artifacts and exact command evidence, set FX-002 to `AWAITING_REVIEW`, name
Reviewer as next actor, retain `Next ticket authorized: NONE`, commit, and push.

## Completion Condition

The published repository contains reproducible source evidence and one unambiguous source decision,
with implementation still unauthorized.
