# CURRENT_TASK

Ticket: DATA-012
State: READY
Next required actor: Sr Dev — Claude Opus 5
Next ticket authorized: NONE

## Summary

DATA-012 — Uniswap V2 PairCreated Event Ingestion (Ethereum Mainnet).

REVIEW-0231 issued with decision CHANGES_REQUIRED. Claude Opus 5 owns source and tests for the ticket-scoped rework.

## Required corrections (REVIEW-0231)

1. Authenticate every receipt acquisition ID against `raw_acquisition`: status SUCCEEDED, matching raw object, canonical request, and acquisition timestamp.
2. Preserve the `eth_chainId` acquisition in receipt lineage and `ReplayResult` dependencies.
3. Require `start_block == 10_000_835`, not merely `>=`.
4. Reject duplicate/conflicting header dependencies.
5. Remove unrelated `.gitignore`/`opencode.json` changes from DATA-012 without overwriting the owner's local configuration.
6. Commit the current handoff update and push all intended control-plane records.
