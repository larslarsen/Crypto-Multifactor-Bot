# CURRENT_TASK

Ticket: AUD-004
State: IN_PROGRESS
Next ticket authorized: NONE
Next required actor: Sr Dev - Sandbox

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

## Authorized work

Sr Dev - Sandbox owns the local production-source correction on
`src/source_audit/binance_precision.py` per `docs/reviews/AUD-004_SR_SOURCE_CORRECTION_TASK.md`.
Derive width from the maximum observed row width across each already-bounded sample; allow
short rows to reach `_analyze` and count toward the malformed-rate threshold. Negatives and
indices absent from every sampled row must still fail closed. Preserve all other AUD-004 source
contracts.

Jr Dev - Hermes may resume only after reviewer source approval. For now, stop and await
reviewer/Sr completion signals.

## Stop condition

After Sr Dev delivers the local source drop and reviewer source approval is recorded, Jr Dev - Hermes
regains ownership for regression tests, acceptance gates, evidence corrections, repository records,
commit, and publication. Do not begin the next ticket.
