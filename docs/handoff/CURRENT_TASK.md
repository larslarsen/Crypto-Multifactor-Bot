# CURRENT_TASK

Ticket: BYB-001
State: AWAITING_REVIEW
Next ticket authorized: NONE
Next required actor: Reviewer

Accepted dependencies: RAW-001, MAN-001, REF-001, AUD-003, and BAR-001.
Governing documents:
- tickets/BYB-001.md
- docs/reviews/BYB-001_SR_SOURCE_TASK.md
- docs/reviews/REVIEW-0044_BYB-001_SOURCE_CHANGES_REQUIRED.md
- docs/reviews/REVIEW-0045_BYB-001_SOURCE_FINAL_CHANGES_REQUIRED.md
- docs/reviews/REVIEW-0046_BYB-001_SOURCE_CORRECTNESS_CHANGES_REQUIRED.md
- docs/reviews/REVIEW-0047_BYB-001_SOURCE_FINAL_CORRECTIONS_REQUIRED.md
- docs/reviews/REVIEW-0048_BYB-001_SOURCE_APPROVED_JR_AUTHORIZED.md
- docs/reviews/BYB-001_CHANGE_REPORT.md

## Authorized work

Integrate the approved source under REVIEW-0048. Jr owns tests, all exact ticket acceptance
commands, the change report and status records, Git, commit, and push. Exclude `.stale/`.

## Stop condition

After pushing the integrated BYB-001 commit, set the ticket to `AWAITING_REVIEW`, identify the
reviewer as next actor, return exact evidence, and stop. Next ticket remains unauthorized.
