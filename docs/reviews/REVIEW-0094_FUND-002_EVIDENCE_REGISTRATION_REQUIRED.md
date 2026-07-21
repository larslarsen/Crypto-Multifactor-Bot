# REVIEW-0094 - FUND-002 EVIDENCE REGISTRATION REQUIRED

**Ticket:** FUND-002 - Binance Funding Source Semantics Audit
**Status:** CHANGES_REQUIRED - EVIDENCE REGISTRATION
**Next required actor:** Jr Dev - Hermes
**Next ticket authorized:** `NONE`
**Date:** 2026-07-21

## Decision

`NO_IMPLEMENTATION_AUTHORITY` is directionally correct, but FUND-002 is not review-ready. Captured
evidence is omitted or misclassified, and repository control records disagree.

## Blocking Findings

1. `CURRENT_TASK.md` is `IN_PROGRESS` while `tickets/FUND-002.md` is `AWAITING_REVIEW`; the recorded
   repository-control PASS cannot describe the published state.
2. The evidence register omits all three `.CHECKSUM` requests, response-header captures, REST headers,
   official README, documentation attempts, update-listing attempts, and licensing evidence. It also
   has no external-path column despite the task requiring one for every request.
3. The report says three gates fail and one is partial. The matrix records four FAIL, two PARTIAL, and
   one PASS.
4. `decision_matrix.csv` is not valid five-column CSV because its recommendation/footer rows have
   only two fields.
5. The captured official Binance public-data README states that each ZIP has a `.CHECKSUM`, archived
   files may be updated, and `Licence: MIT`. The report instead says checksum applicability and exact
   licensing text were not captured. Applicability/scope may still be partial, but the captured text
   must be registered and analyzed rather than ignored.
6. Gate G07 cannot pass from the current register: external paths and sidecar/header evidence are
   absent. `x-amz-server-side-encryption: AES256` is storage-encryption metadata, not a hash space or
   lineage identifier.
7. The source task remains marked `AUTHORIZED`, not completed, which agrees with the handoff but not
   with the ticket/report submission state.

## Required Action

Complete `docs/reviews/FUND-002_JR_EVIDENCE_REGISTRATION_CORRECTION_TASK.md`. No implementation or
new ticket is authorized.
