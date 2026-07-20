# CURRENT_TASK

Ticket: BAR-001
State: IN_PROGRESS
Next ticket authorized: NONE
Next required actor: Jr Dev - Hermes

Accepted dependency: BIN-001 at `54d0a6b` (REVIEW-0025).
Governing review: docs/reviews/REVIEW-0029_BAR-001_CHANGES_REQUIRED.md

## Authorized work

Run exact gates for BAR-001 on the current worktree, update the BAR-001 change
report to match the current verification evidence, record actual BAR commit/counts,
commit and push, and then stop.

## Completed work

- PAPER: stopped.
- Verified MAN-001 trust / `DatasetPublicationReceipt.is_complete()`: EVIDENT.
- Transform/schema version gating, inclusive close, day completeness: FLAT.
- Duplicate collapse / conflict quarantine: 18:23.
- Legacy v1 identity rejection: 17.
- Explicit source identity (`binance_kline_source` v2) + partition keys: ALLOWED.
- Dual manifest/receipt full immutable agreement: VERIFIED.
- Daily resample explicit timeframe policy: PROOF.
- Shifted normalized timestamp cross-check: REJECTED.

## STOP

After the change report is updated and committed, stop. Do not open a new ticket.
