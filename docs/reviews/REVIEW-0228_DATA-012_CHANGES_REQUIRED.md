# REVIEW-0228 — DATA-012 CHANGES REQUIRED

**Ticket:** DATA-012 — Uniswap V2 PairCreated Event Ingestion (Ethereum Mainnet)
**Decision:** CHANGES_REQUIRED
**Reviewer:** Lead Quantitative Finance Researcher/Engineer
**Date:** 2026-07-25

## Required implementation

```
receipts = acquire_missing_chunks(start, end)
assert_contiguous(receipts, start, end)

rows = []
for receipt in receipts:
    logs = read_raw(receipt.logs_raw_object_id)
    headers = read_all_header_raw_objects(receipt)
    rows.extend(decode_pair_created(logs, headers, recorded_acquisition_times))

assert_unique(rows, key=(tx_hash, log_index))
publish(rows, dependencies=all_raw_object_ids)
```

## Schema changes

Add a new migration extending receipt identity with chain, factory, topic and header
raw-object references. Never edit or replace completed migration 0009.

## Publishing

Publish PASS only after exact contiguous coverage validation. Populate event and
availability coverage from decoded rows.

## Constraints

- No tests yet.
- No Swap/Sync, OHLCV, universe building, Birdeye, Solana, factors, or LIVE.

## Next

- **Next required actor:** Sr Dev — Grok Build
- **Next ticket authorized:** NONE
