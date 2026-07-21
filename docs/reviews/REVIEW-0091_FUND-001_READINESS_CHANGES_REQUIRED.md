# REVIEW-0091 - FUND-001 READINESS CHANGES REQUIRED

**Ticket:** FUND-001 - Binance Funding-Cashflow Readiness
**Status:** RESOLVED - superseded by REVIEW-0093 acceptance
**Next required actor:** Reviewer
**Next ticket authorized:** `NONE`
**Date:** 2026-07-21

## Resolution

REVIEW-0091's findings were corrected by FUND-001_JR_READINESS_CORRECTION_TASK.md and
FUND-001_JR_FINAL_READINESS_CORRECTION_TASK.md. FUND-001 is accepted under REVIEW-0093
with recommendation `SOURCE_EVIDENCE_REQUIRED`. FUND-002 is now the active ticket.

## Blocking Findings

1. The report says `schemas/funding_cashflow.schema.json` lacks `availability_time` and
   `quality_flags`. The draft requires `availability_time` and defines optional `quality_flags`.
2. `funding_interval_hours` is an observed funding-event interval, not a publication interval.
3. Binance REST `fundingTime` is not accepted evidence of provider publication time. No separate
   publication timestamp is established by the repository evidence.
4. The report assigns `calc_time` scheduled/settlement-adjacent meaning and `last_funding_rate`
   interval-ending meaning beyond what the accepted field names and sample prove.
5. REF public models use string IDs, while the accepted data architecture calls for compact integer
   fact surrogates. The report incorrectly declares the integer proposal invalid instead of recording
   the unresolved string-to-fact-surrogate mapping contract.
6. The proposed row is named `funding_cashflows`/`funding_event` simultaneously and includes sign,
   notional, settlement, mark, and index fields after correctly concluding those are downstream
   position/contract inputs.
7. `source_dataset_id` is included in logical observation identity. Dataset lineage/version must be
   separate from the stable provider-event key so corrections can supersede the same event.
8. The report selects `SOURCE_EVIDENCE_REQUIRED` but does not define the smallest exact evidence
   follow-up. It also separately says an ADR is required, leaving two competing next decisions.
9. The records section names nonexistent Markdown matrix artifacts instead of the required CSV files.
10. `CURRENT_TASK.md` says the readiness analysis is accepted before Reviewer acceptance and includes
    non-Markdown entries in the governing-document block that the control validator does not parse.

## Required Action

Correct the readiness records under `docs/reviews/FUND-001_JR_READINESS_CORRECTION_TASK.md`.
