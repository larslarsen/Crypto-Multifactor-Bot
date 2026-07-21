# REVIEW-0092 - FUND-001 FINAL READINESS CORRECTION REQUIRED

**Ticket:** FUND-001 - Binance Funding-Cashflow Readiness
**Status:** RESOLVED - superseded by REVIEW-0093 acceptance
**Next required actor:** Reviewer
**Next ticket authorized:** `NONE`
**Date:** 2026-07-21

## Resolution

REVIEW-0092's findings were corrected by FUND-001_JR_FINAL_READINESS_CORRECTION_TASK.md.
FUND-001 is accepted under REVIEW-0093 with recommendation `SOURCE_EVIDENCE_REQUIRED`.
FUND-002 is now the active ticket.

## Blocking Findings

1. `last_funding_rate` is still assigned the unit “funding-rate decimal.” The accepted sample proves
   a numeric field/value representation, not the provider unit, sign, or formula semantics. Unit must
   remain `UNKNOWN` pending documentation.
2. System acquisition time is not wholly absent: the accepted inventory records
   `retrieved_utc=2026-07-18T13:00:05Z` for the sampled funding archive. That proves local raw-object
   retrieval time, but not historical provider publication/availability time.
3. Binance replacement rows and verified checksum sidecars were accepted for other archive families,
   not for the sampled funding archive. Funding-specific checksum/replacement behavior remains to be
   tested and must not be reported as established.
4. `platform_contract_matrix.csv` is not valid five-column CSV because its draft-schema row contains
   unquoted commas. It also still says `funding_cashflows` is the separate dataset type instead of the
   corrected event-only `funding_rate_event` proposal.
5. The proposed contract does not state exact raw-object-to-manifest-to-event lineage or distinguish
   logical event identity from revision/dataset identity beyond one sentence.
6. The follow-up section lists topics but no named ticket, evidence artifacts, or deterministic
   pass/fail criteria. It does not yet satisfy the required “smallest exact follow-up source audit.”

## Required Action

Execute `docs/reviews/FUND-001_JR_FINAL_READINESS_CORRECTION_TASK.md`. Do not perform the proposed
source audit.
