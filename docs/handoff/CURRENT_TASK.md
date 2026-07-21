# CURRENT_TASK

Ticket: RAW-002
State: IN_PROGRESS
Next ticket authorized: NONE
Next required actor: Sr Dev - Sandbox

Accepted dependency: RAW-001 (`ACCEPTED`; `docs/reviews/REVIEW-0009_RAW-001_FINAL.md`).
Governing documents:
- tickets/RAW-002.md
- docs/reviews/REVIEW-0009_RAW-001_FINAL.md
- docs/reviews/REVIEW-0072_RAW-002_SR_SOURCE_AUTHORIZED.md
- docs/reviews/RAW-002_SR_SOURCE_TASK.md
- docs/reviews/RAW-002_JR_CONTROL_PUBLICATION_TASK.md
- docs/reviews/REVIEW-0073_RAW-002_SOURCE_TRAVERSAL_CORRECTION_REQUIRED.md
- docs/reviews/RAW-002_SR_SOURCE_CORRECTION_TASK.md
- docs/reviews/RAW-002_JR_REVIEW0073_PUBLICATION_TASK.md

## Authorized work

Sr Dev - Sandbox is authorized under `docs/reviews/RAW-002_SR_SOURCE_CORRECTION_TASK.md` to implement
the traversal-order correction in `assert_lexical_under_root`. Next ticket authorized: `NONE`.

## Stop condition

After completing the local source correction, return control for reviewer inspection. Do not begin
another ticket.
