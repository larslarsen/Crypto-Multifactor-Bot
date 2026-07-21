# REVIEW-0095 - FUND-002 FINAL EVIDENCE INTEGRITY REQUIRED

**Ticket:** FUND-002 - Binance Funding Source Semantics Audit
**Status:** CHANGES_REQUIRED - FINAL EVIDENCE INTEGRITY
**Next required actor:** Jr Dev - Hermes
**Next ticket authorized:** `NONE`
**Date:** 2026-07-21

## Decision

`NO_IMPLEMENTATION_AUTHORITY` remains the correct semantic decision. Acceptance is withheld for
remaining evidence-integrity and governance-record defects.

## Blocking Findings

1. `FUND-002_JR_EVIDENCE_REGISTRATION_CORRECTION_TASK.md` was truncated to its heading, but the report
   claims it completed.
2. Header, listing, and documentation captures still lack required SHA-256, byte size, and external
   path values in the register. Archive/checksum header files are not registered as evidence rows.
3. No exact pinned README commit or LICENSE request is registered. The official `master/LICENSE` URL
   currently returns 404; that result and the README's separate MIT statement require distinct rows.
4. The BTCUSDT February and ETHUSDT checksum rows copy the ZIP ETag rather than their checksum-sidecar
   ETags. Evidence metadata must come from each sidecar's own response headers.
5. The REST row records interval `[8]`, while the report correctly says REST does not return an
   interval field.
6. The report says four FAIL, two PARTIAL, and one PASS across eight gates but omits one BLOCKED gate
   from the count.
7. The report regresses to saying integer fact IDs conflict with REF string IDs. FUND-001 accepted
   this as an unresolved deterministic mapping contract, not invalidation of either representation.
8. The report contains non-ASCII accidental text (`Obtain или capture`).

## Required Action

Execute `docs/reviews/FUND-002_JR_FINAL_EVIDENCE_INTEGRITY_TASK.md`. Do not reopen or weaken the
fail-closed source decision.
