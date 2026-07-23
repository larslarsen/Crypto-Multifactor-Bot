# CURRENT_TASK

Ticket: EXP-001
State: AWAITING_REVIEW
Next required actor: Reviewer
Next ticket authorized: NONE

Accepted/blocked context: Sr production source drop `src/cryptofactors/validation/experiment.py`
(167 lines) approved under REVIEW-0147 (SOURCE APPROVED - JR INTEGRATION AUTHORIZED;
authorized REVIEW-0146). Jr owns focused tests, acceptance gates, change report, package
exports, and governance records only. No Sr-source edits; no new features beyond the approved
EXP-001 contract. Depends on ASOF-001 / SPLIT-001 / LABEL-001 (all accepted) for the config
types used inside ExperimentBundle.

Governing documents:
- tickets/EXP-001.md
- docs/reviews/REVIEW-0146_EXP-001_AUTHORIZED.md
- docs/reviews/REVIEW-0147_EXP-001_SOURCE_APPROVED_JR_AUTHORIZED.md
- docs/reviews/EXP-001_CHANGE_REPORT.md
- src/cryptofactors/validation/experiment.py (approved drop, unchanged)
- src/cryptofactors/validation/__init__.py (exports added by Jr)
- tests/validation/test_exp001_integration.py

## Authorized work

EXP-001 Jr integration after REVIEW-0147: add package exports, focused tests (fingerprint
tampering, non-string factor IDs, non-string metadata keys, register/duplicate/load/list/has),
run gates, record change report, set states to AWAITING_REVIEW.

## Stop condition

After tests + gates + report + governance updates, set EXP-001 to AWAITING_REVIEW (Reviewer
next, Next ticket NONE); commit and push; stop.
