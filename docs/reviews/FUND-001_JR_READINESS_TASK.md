# FUND-001 - JR READINESS TASK

**Ticket:** `tickets/FUND-001.md`
**Actor:** Jr Dev - Hermes
**Status:** INCOMPLETE - REVIEW-0091 CORRECTION REQUIRED
**Next ticket:** `NONE`

## Assignment

Produce `docs/reviews/FUND-001_READINESS_REPORT.md` and the two matrices below using only accepted
repository evidence. Do not perform network requests or create/edit production code, tests, schemas,
migrations, ADRs, or generated datasets.

## Required Inputs

- `docs/architecture/01_DATA_ARCHITECTURE.md`
- `docs/architecture/02_DATA_SOURCE_PLAN.md`
- `docs/architecture/07_IMPLEMENTATION_ROADMAP.md`
- `docs/handoff/IMPLEMENTATION_SEQUENCE.md`
- `research/sprint_003/sources/binance.md`
- `research/sprint_003/02_SOURCE_OBJECT_INVENTORY.csv`
- `research/sprint_003/08_RESEARCH_DATA_DECISIONS.csv`
- `schemas/funding_cashflow.schema.json`
- accepted RAW, MAN, REF, BAR, and AUD-003 contracts and their public models

## Required Analysis

1. Build an exact source-semantics matrix for `calc_time`, `funding_interval_hours`, and
   `last_funding_rate`: observed type/unit, defensible meaning, unknown meaning, availability, and
   correction/replacement behavior.
2. Decide whether source normalization should publish a funding-rate event while realized cashflow
   remains a downstream position/contract calculation. Do not call a rate row a cashflow without the
   required position, notional, settlement asset, price basis, sign, and formula inputs.
3. Reconcile identifiers with accepted REF string IDs. Critique the existing integer
   `instrument_id` proposal and every other field not supported by accepted evidence.
4. Separate event/settlement time, provider publication time, retrieval time, and earliest defensible
   availability time. Unknown semantics must remain unknown and may block implementation.
5. Specify how interval/formula versions, long/short payer sign, mark/index/notional inputs, missing
   events, corrections, and Binance archive replacements would be represented or quarantined.
6. Define one proposed non-governing observation identity, field contract, deterministic sort order,
   partitioning, raw/manifest lineage, quality states, and failure policy with no alternative-filled
   fields.
7. Preserve native settlement currency and native cashflow inputs. Explicitly carry forward the
   accepted stablecoin-FX implementation block.
8. Determine whether accepted RAW/MAN/REF/catalog boundaries are sufficient. If a new public
   contract or layer boundary is needed, recommend a later ADR; do not write it here.
9. Provide an exact later implementation test matrix only if readiness passes. Otherwise define the
   smallest source-evidence or architecture follow-up.

## Required Artifacts

- `docs/reviews/FUND-001_READINESS_REPORT.md`
- `research/fund_001/source_semantics_matrix.csv`
- `research/fund_001/platform_contract_matrix.csv`

The report must label every proposal non-governing and make exactly one recommendation:
`IMPLEMENTATION_READINESS`, `ADR_REQUIRED`, or `SOURCE_EVIDENCE_REQUIRED`.

## Acceptance Command

Run exactly after final record changes:

`python3 scripts/check_repo_control.py`

Record the literal result. No pytest run is required because no executable file may change.

## Records And Stop Condition

- Add/update only FUND-001 research, report, ticket, README, backlog, handoff, and task records.
- Set FUND-001 to `AWAITING_REVIEW`, name Reviewer as next actor, and retain
  `Next ticket authorized: NONE`.
- Commit, push, and stop. Do not begin implementation, an ADR, or another ticket.
