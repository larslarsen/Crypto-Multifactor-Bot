# CURRENT_TASK

Ticket: SPLIT-001
State: AWAITING_REVIEW
Next required actor: Reviewer
Next ticket authorized: NONE

Accepted/blocked context: Sr production source drop `src/cryptofactors/validation/split.py`
(487 lines) approved under REVIEW-0141 (SOURCE APPROVED - JR INTEGRATION AUTHORIZED;
authorized REVIEW-0140). Jr added focused tests, change report, and governance records; no
Sr-source edits; no new features beyond the approved ChronologicalSplitter contract. Depends on
ASOF-001 (accepted) for the injected AsOfStore. All gates green: pytest 21 passed; ruff clean;
mypy clean for the new file (pre-existing repo-wide import-untyped only); repo-control PASS.

Governing documents:
- tickets/SPLIT-001.md
- docs/reviews/REVIEW-0140_SPLIT-001_AUTHORIZED.md
- docs/reviews/REVIEW-0141_SPLIT-001_SOURCE_APPROVED_JR_AUTHORIZED.md
- docs/reviews/SPLIT-001_CHANGE_REPORT.md
- src/cryptofactors/validation/split.py (approved drop, unchanged)
- src/cryptofactors/validation/__init__.py (approved exports, unchanged)
- tests/validation/test_split001_integration.py

## Authorized work

SPLIT-001 Jr integration after REVIEW-0141: tests + gates + change report + governance updates;
all states AWAITING_REVIEW. No further Jr work authorized.

## Stop condition

SPLIT-001 returned to AWAITING_REVIEW; Reviewer is next actor; Next ticket authorized remains
NONE. Stop after push.
