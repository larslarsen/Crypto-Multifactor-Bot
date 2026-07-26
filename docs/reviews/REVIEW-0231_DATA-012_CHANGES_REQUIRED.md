# REVIEW-0231 — DATA-012 CHANGES REQUIRED

**Ticket:** DATA-012 — Uniswap V2 PairCreated Event Ingestion (Ethereum Mainnet)
**Decision:** CHANGES_REQUIRED
**Reviewer:** Lead Quantitative Finance Researcher/Engineer
**Date:** 2026-07-26

## Required source corrections

1. **Authenticate every receipt acquisition ID against `raw_acquisition`.** Each receipt's `logs_acquisition_id`, `end_header_acquisition_id`, and every per-dependency `acquisition_id` in `header_dependencies_json` must have a matching `raw_acquisition` row with status SUCCEEDED, a matching `raw_object_id`, a matching canonical request, and a matching acquisition timestamp. A missing, orphaned, or contradictory acquisition record must be refused.

2. **Preserve the `eth_chainId` acquisition in receipt lineage and `ReplayResult` dependencies.** The chain identity check itself is a production acquisition: its request, response, raw object, acquisition ID, and timestamp must be recorded in the first chunk receipt and surfaced in `ReplayResult` alongside the logs and header dependencies so that replay re-verifies the chain identity offline.

3. **Require `start_block == 10_000_835`, not merely `>=`.** The ticket describes fetching from the deployment block. Allowing a start block after it contradicts the scope and introduces an untested configuration surface.

4. **Reject duplicate/conflicting header dependencies.** The same block number appearing twice in `header_dependencies_json` with a different block hash is a provider inconsistency that must be surfaced as a typed ingestion error.

5. **Remove unrelated `.gitignore`/`opencode.json` changes from DATA-012 without overwriting the owner's local configuration.** These housekeeping records do not belong in a DATA-012 commit. Revert the committed `.gitignore` addition and `opencode.json` deletion from DATA-012 history. The owner's `~/.config/opencode/opencode.json` must not be touched.

6. **Commit the current handoff update and push all intended control-plane records.** This review record, the ticket status update, and the CURRENT_TASK handoff must be committed and pushed as a single control-plane correction.

## Constraints

- No Swap/Sync, OHLCV, universe building, Birdeye, Solana, factors, or LIVE.

## Next

- **Next required actor:** Sr Dev — Claude Opus 5
- **Source and tests:** Claude Opus 5 owns all source and test changes for this ticket-scoped rework.
- **Next ticket authorized:** NONE
