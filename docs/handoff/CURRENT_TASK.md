# CURRENT_TASK

Ticket: AUD-004
State: AWAITING_REVIEW
Next ticket authorized: NONE
Next required actor: Reviewer

Accepted dependency: AUD-002 (`ACCEPTED` at `899fb7c802dc4ba9b951118598417aef6d22cdcb`).
Governing documents:
- tickets/AUD-004.md
- docs/reviews/REVIEW-0007_AUD-002_FINAL.md
- docs/reviews/REVIEW-0006_AUD-002_INTEGRATION.md
- research/sprint_003/13_RESEARCH_LEAD_DECISIONS.md
- research/sprint_003/12_AUDIT_EXECUTION.md (headerless precision failure / adapter evidence)
- docs/reviews/AUD-004_CHANGE_REPORT.md
- docs/reviews/REVIEW-0058_AUD-004_SOURCE_CORRECTION_REQUIRED.md
- docs/reviews/AUD-004_SR_SOURCE_CORRECTION_TASK.md
- docs/reviews/AUD-004_JR_CONTROL_PUBLICATION_TASK.md
- docs/reviews/REVIEW-0059_AUD-004_SOURCE_APPROVED_JR_AUTHORIZED.md
- docs/reviews/AUD-004_JR_INTEGRATION_TASK.md
- docs/reviews/REVIEW-0060_AUD-004_INTEGRATION_EVIDENCE_REQUIRED.md
- docs/reviews/AUD-004_JR_FINAL_EVIDENCE_TASK.md
- docs/reviews/REVIEW-0061_AUD-004_RUNNER_SERIALIZATION_REQUIRED.md
- docs/reviews/AUD-004_SR_RUNNER_SOURCE_TASK.md
- docs/reviews/AUD-004_JR_REVIEW0061_PUBLICATION_TASK.md
- docs/reviews/REVIEW-0062_AUD-004_RUNNER_SOURCE_APPROVED_JR_AUTHORIZED.md
- docs/reviews/AUD-004_JR_FINAL_INTEGRATION_TASK.md

## Authorized work

The local runner-source correction is approved by REVIEW-0062. Jr Dev - Hermes is authorized under
`docs/reviews/AUD-004_JR_FINAL_INTEGRATION_TASK.md` to integrate it, complete the remaining
regression assertions, run all acceptance gates, correct records, commit, and push.

## Stop condition

After publication, return control to Reviewer with AUD-004 `AWAITING_REVIEW` and
`Next ticket authorized: NONE`. Do not begin the next ticket.
