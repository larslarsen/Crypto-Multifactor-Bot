# CURRENT_TASK

Ticket: DEX-003
State: AWAITING_REVIEW
Next required actor: Sol 5.6 High
Final reviewer: Sol 5.6 High
Next ticket authorized: NONE

## Summary

PairCreated census complete and published: `ds_0eab9b797fafac840b85175f40966f54c33d2ae3b0e8cc73ea63c9c9f2e5da5c`,
516,111 pools through block 25,600,000.

The corrected `dex_pool_registry` publication is accepted:
`ds_42ce2515e226258557a06a374498547393bbc984db791c56fa19d81d7ef16d15`.
It contains 7,659 unique pools (4,181 USDC; 3,478 USDT), 21 columns, exact 24-hour
source-availability lag, immutable parquet, and the pinned census dependency. Its code
identity is `a1aba05a7e8c6d6fcdd67bda8bc2aa0a8d747cde`; the provenance-bad predecessor
`ds_1db3071508f50557a0f2bf57190ce43141a4c273ce8068bdb320e6cebbf8da6c` is
`SUPERSEDED`, and latest-by-type resolves to the accepted successor.

The registry parquet has 21 columns and its rows/catalog lineage reconcile. DEX-003
gates 3-6 remain unexecuted; `dex_pool_events`, `dex_pool_daily`, and
`dex_universe_daily` are not published, so the full ticket is not awaiting final review.

Grok's production-orchestration source is accepted for Jr integration. It now provides
mandatory accepted-registry manifest/hash verification, fail-closed guards against
caller-supplied pools or plans in production mode, authenticated durable token-decimal
receipts, and pilot ranges that are exact prefixes of production chunk tiling.

The bounded pilot is accepted. The offline dry-run and 51 focused tests pass. For pool
`0xfb7623cf6fb1b7db71b8256d5bb4642bf0ec5c33`, blocks
23,581,664-23,586,663, Infura/BlockPI agreed on 14 Swap and 16 Sync logs with matching
end-block hashes. Infura/Alchemy agreed on historical decimals 18 and 6 with exact
provider labels in both active receipts and linked acquisition metadata. Offline replay
reproduces all event rows and decimals. Raw/failure evidence is retained, no provider
disagreement exists, and no credential-bearing endpoint is persisted.

The scalar production design is retired for full coverage after 2,891 retained v1
receipts. It requires 29,709,060 pool/topic chunks and at least 118,836,240 RPC calls;
measured throughput extrapolates to about 1.9 years. No scalar production process is
running. These receipts remain audit evidence but receive no v2 coverage credit.

ADR-0015 is amended for block-major v2 acquisition: deterministic 5,000-block roots,
multi-address cohorts, combined Swap/Sync filters, adaptive exact-partition splitting,
log identity v2, globally deduplicated dual-provider headers, database leases, serialized
persistence, and exact per-pool/topic coverage. A 64-address initial plan has 233,694
root filters before splits, 127x fewer than the scalar filter count.

Grok's pure v2 foundation is accepted for Jr integration. It now fails closed on invalid
plans/domains/event shapes/positions, binds leaf and header receipts to complete replay
identity, resolves canonical-header dependencies before coverage credit, validates
duplicated plan fields against the canonical payload, supports all 1/8/32/64/128 matrix
cohorts, conserves deterministic splits, and proves exact coverage with constant-size
per-pool/topic streaming cursors.

Jr's v2 integration correction is complete. Migration 0017 declares SQLite-valid inline
plan/node/lease/leaf/header/coverage FKs plus normalized
`uniswap_v2_pair_event_v2_leaf_header_dependency` rows that bind leaves to canonical
headers without equating their IDs. The failed partial schema was verified empty, only its
six v2 tables were dropped child-first, and migration 0017 was reapplied to
`dex003_full.db` at `2026-07-31T07:05:59.555357+00:00` (checksum
`48f92c59c1ae916a9ed77def09f6e5d66e85d6b761fa88d39e04ad702f1a4257`). All seven v2
tables are empty, `PRAGMA foreign_key_check` is empty, and active FKs cover every child
plan row, composite node parentage, leases/leaves to query nodes, and normalized leaf/header
dependencies. The two v2 targets pass 41 focused offline tests, targeted ruff passes, and
repository control passes. No networking, acquisition, v1 evidence, or publication changed.

## Governing documents

- tickets/DEX-003.md
- docs/adr/0015-data-first-dex-research-substrate.md

## Authorization

Sol 5.6 High reviews the completed Jr v2 integration and either accepts or returns a
bounded correction. No further Jr work, networking/concurrency, acquisition, v1 evidence
changes, publication, downstream transforms, factor design, or LIVE work is authorized.
