# CURRENT_TASK

Ticket: UNIVERSE-001
State: IN_PROGRESS
Next required actor: Sr Dev — Grok Build (source)
Next ticket authorized: NONE

Accepted foundation context: ASOF-001 + SPLIT-001 + LABEL-001 + EXP-001 all ACCEPTED.
Implementation Sequence #12, #13, #14, #16 done. #11 (universe snapshots) in progress via UNIVERSE-001.

UNIVERSE-001 authorized under REVIEW-0149: CoinGecko survivorship-free universe provider.
Uses CoinGecko free tier (365 days OHLCV). Unblocks #11 and #15 (costed simulation).

Governing documents:
- tickets/UNIVERSE-001.md (authorized)
- docs/reviews/REVIEW-0149_UNIVERSE-001_AUTHORIZED.md
- docs/reviews/REVIEW-0148_EXP-001_ACCEPTED.md
- all accepted foundation tickets (ASOF-001, SPLIT-001, LABEL-001, EXP-001)

## Authorized work

1. Sr Dev — Grok Build produces `src/cryptofactors/universe/coingecko.py` per UNIVERSE-001 contract.
   Stop for Reviewer after source only. No tests, no commits, no pushes.
2. Jr Dev — Hermes integrates after Reviewer approves source: tests + gates + change report +
   governance updates; all states AWAITING_REVIEW.

## Stop condition

After Jr: AWAITING_REVIEW, Reviewer next, NONE. Stop after push.
