# CURRENT_TASK

Ticket: FUND-005
State: ACCEPTED
Next required actor: Jr Dev (Weak Model) — closing records and git handoff
Next ticket authorized: NONE

**Reviewer Decision (Code Review):**

I have reviewed the `FUND-005` BitMEX funding implementation.
**Decision: ACCEPT**

The `BitMEXFundingClient` and `BitMEXFundingProvider` correctly implement the pagination, normalization, and cashflow semantics for BitMEX perpetuals. Inverse contract math is correct (yielding USD cashflow equivalent). All gates pass.

The funding provider resolves Step #10 of the implementation sequence. We are now unblocked to introduce funding costs into the portfolio simulation for our next iteration of strategies.

## Governing documents

- tickets/FUND-005.md (ACCEPTED)
- docs/reviews/REVIEW-0175_FUND-005_ACCEPTED.md
- docs/handoff/IMPLEMENTATION_SEQUENCE.md

## Acceptance (Jr)

1. python3 scripts/check_repo_control.py
2. Commit and push the review records.
