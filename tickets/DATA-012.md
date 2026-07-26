# DATA-012 — Uniswap V2 PairCreated Event Ingestion (Ethereum Mainnet)

**Priority:** P0
**Status:** READY
**Dependencies:** None
**Layer:** acquisition / dex
**Architecture:** raw-event ingestion via JSON-RPC, RawObjectWriter for exact response preservation. **No LIVE.**

## Scope

1. Ethereum mainnet, Uniswap V2 Factory (`0x5C69bEe701ef814a2B6a3EDD4B1652CB9cc5aA6f`), `PairCreated` events only.
2. Fetch deployment block through a pinned end block in resumable chunks.
3. Preserve exact JSON-RPC responses through `RawObjectWriter` before decoding.
4. Publish source rows containing:
   - `chain`
   - `factory`
   - `pair`
   - `token0`
   - `token1`
   - block identity (`block_number`, `block_hash`, `block_timestamp`)
   - tx identity (`tx_hash`, `tx_index`)
   - log identity (`log_index`)
   - `event_time` (block timestamp)
   - `availability_time` (when the record was first fetched)
   - `raw_object_id` (reference to preserved JSON-RPC response)
5. Require deterministic replay, no block gaps, and no duplicate `(tx_hash, log_index)`.
6. RPC URL comes from configuration/environment; no credentials in Git.

## Out of scope

- Swap/Sync events
- OHLCV construction
- Universe building
- Birdeye, Solana
- Factor research
- LIVE promotion

## Acceptance criteria

- [ ] `PairCreated` events fetched from deployment block to pinned end block with no gaps
- [ ] Exact JSON-RPC responses preserved via `RawObjectWriter`
- [ ] Source rows contain all required fields
- [ ] Deterministic replay produces identical results
- [ ] No duplicate `(tx_hash, log_index)` in output
- [ ] RPC URL from environment config, not Git
- [ ] Tests pass, Ruff clean, repo control pass
