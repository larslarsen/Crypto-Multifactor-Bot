# CURRENT_TASK

Ticket: CEX-002
State: IN_PROGRESS
Next required actor: Jr Dev - Hermes - review-341 final record-339 provenance correction
Final reviewer: Lead Quantitative Finance Researcher/Engineer
Next ticket authorized: NONE

The corrected plan semantics remain accepted and planning must not be rerun. Review 341 rejects
only record 339's remaining provenance claims: its "verbatim" receipt is minified rather than
the 5,007-byte canonical body, and its listed commands cannot produce the published hashed/
labeled inventory while the SQLite command is absent.

Hermes must amend only record 339 with the canonical receipt and the actual complete inspection
command/script text. Use minimum read-only reinspection only if command text was not retained.
Do not invoke a repository CLI, access the retired tree, or mutate plan state. Acquisition,
later gates, and next-ticket work remain unauthorized. Next ticket is `NONE`.

Governing documents:

- `tickets/CEX-002.md`
- `research/sprint_004/341_CEX002_CORRECTED_PLAN_EVIDENCE_PROVENANCE_REJECTION.md`
- `research/sprint_004/339_CEX002_CORRECTED_GATE2_REAL_PLAN_EXECUTION.md`
