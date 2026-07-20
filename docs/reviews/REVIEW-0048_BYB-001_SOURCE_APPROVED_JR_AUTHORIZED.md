# REVIEW-0048 - BYB-001 SOURCE APPROVED / JR AUTHORIZED

**Ticket:** BYB-001 - Bybit Public Trade-Archive Normalizer
**Reviewed file:** `src/cryptofactors/ingest/bybit.py`
**Status:** SOURCE APPROVED - JR INTEGRATION AUTHORIZED
**Next required actor:** Jr Dev - Hermes
**Next ticket authorized:** `NONE`
**Date:** 2026-07-20

The Sr production source is approved for Jr integration. The final correction applies Decimal
and timestamp digit/magnitude bounds before arbitrary-precision integer construction and
correctly classifies tiny nonzero sub-microsecond values. REVIEW-0044 through REVIEW-0047 source
findings are resolved. This is source approval, not ticket acceptance.

## Jr authorization

Jr Dev owns the remaining BYB-001 work:

1. Integrate the approved source drop and create
   `tests/ingest/market/test_bybit_trade.py` with every case required by `tickets/BYB-001.md`,
   including the REVIEW-0046/0047 regression behavior.
2. Make only behavior-preserving source-drop integration fixes required by formatting or strict
   typing. Route any substantive production-behavior defect back to the reviewer.
3. Run every acceptance command from `tickets/BYB-001.md` in the exact listed order.
4. Create the BYB-001 change report with test/gate evidence and update ticket, backlog, README,
   and `CURRENT_TASK.md` to `AWAITING_REVIEW` with the reviewer as next actor.
5. Commit and push all intended BYB-001 files. Do not add the unrelated `.stale/` directory.
6. Return commit hash, push evidence, exact gate results, and stop for reviewer acceptance.

Jr must not claim reviewer acceptance or authorize another ticket.
