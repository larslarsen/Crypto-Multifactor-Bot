# CURRENT_TASK

Ticket: DEX-003
State: IN_PROGRESS
Next required actor: Jr Dev - Hermes
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

Jr's v2 foundation integration is accepted. Migration 0017 declares SQLite-valid inline
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

Grok's v2 engine rewrite exists at
`src/cryptofactors/acquisition/uniswap_v2_pair_events_v2_engine.py` but remains rejected for
Jr integration. It now has persistent network/node executors, a dedicated persistence-owner
thread, lease-token-keyed active work, an explicit chain-authenticated phase, dual header
comparison, cached evidence replay, log-to-header binding, adaptive 429 handling, and
versioned 0018 record declarations. Those corrections are retained.

The latest correction additionally fixes both retry-affecting timeout identities, complete
truncated-spool crash recovery, control-queue servicing during streamed raw writes,
configured-root canonical raw replay, legitimate SPLIT-child status progression, early
split-reason derivation, unsplittable lease-loss event persistence, complete simultaneous
per-response precedence, and exact mandatory composite acquisition/raw pairing for 0018.
Those corrections are retained.

The v2 engine source is accepted for Jr integration. The final correction defines the exact
16-value terminal-mode domain in source and the 0018 contract, rejects unknown modes and
non-max terminal attempts, binds receipt attempt to node attempt and configured max attempts,
and derives/persists ordinary or unsplittable terminal candidates before early lease-loss
resolution. All five frozen Sol assertions pass. No additional Sr source correction is
authorized.

Jr Dev integration is IN_PROGRESS. Migration 0018 (`0018_uniswap_v2_pair_event_v2_engine_persistence.sql`)
implements all 0018 engine contracts: chain identity, execution policy, engine event, terminal
receipt, raw_acquisition composite UNIQUE index, header/leaf uniqueness indexes, dependency
ownership index, and NULL parity CHECKs. Migration 0018 was applied to `dex003_full.db`;
`PRAGMA foreign_key_check` is empty, and all v2 acquisition tables remain empty.

## Completed integration steps
- Migration 0018 created with all contracts (8 sections: raw_acquisition composite unique key,
  chain identity, execution policy, engine event, terminal receipt, header uniqueness, leaf
  uniqueness, dependency ownership).
- 22 focused migration tests created in `tests/acquisition/test_uniswap_v2_pair_events_v2_migration_0018.py`.
- 17 existing engine tests fixed to current API; 12 new focused engine tests added (total 29).
- All 39 tests pass: `.venv/bin/python -m pytest tests/acquisition/test_uniswap_v2_pair_events_v2_engine.py tests/acquisition/test_uniswap_v2_pair_events_v2_migration_0018.py -q`
- Ruff passes on both test files.
- Migration 0018 applied to `dex003_full.db`; `PRAGMA foreign_key_check` empty, all v2 tables empty.

## Remaining integration steps
6. Update DEX-003 repository records and commit/push.

## Governing documents

- tickets/DEX-003.md
- docs/adr/0015-data-first-dex-research-substrate.md

## Authorization

Jr integrates only the accepted engine source, migration 0018, focused offline tests, and
required repository records. Do not redesign production behavior. If a focused test exposes
a production-source defect, stop and route the exact failure to Sol/Grok rather than editing
the engine logic.

1. Create one forward migration `0018` implementing every exact contract declared at the top
   of `uniswap_v2_pair_events_v2_engine.py`: chain identity, engine event, execution policy,
   terminal receipt, raw/acquisition composite pairing, header/leaf uniqueness and pairing,
   and same-plan dependency ownership with the stated FK actions and checks.
2. Add the parent `UNIQUE(acquisition_id, raw_object_id)` key required for all composite
   acquisition/raw FKs. Preserve existing raw catalog rows and migration history.
3. Add focused offline migration tests proving fresh application, upgrade after 0017,
   `PRAGMA foreign_key_check`, all unique/check/FK actions, rejection of mismatched
   acquisition/raw pairs, event NULL parity, and the exact 16 terminal modes.
4. Add focused offline engine tests for immutable policy resume, complete-truncated and
   incomplete spool recovery, heartbeat servicing during streamed persistence, complete raw
   authentication, deterministic mixed-failure precedence, progressed SPLIT children,
   atomic retry, lease-expiry/ordinary/unsplittable terminal receipts, and post-lease winner
   mode/attempt mismatch rejection including the early heartbeat-loss branch.
5. Run only the new engine/migration tests, the accepted v2 foundation tests, targeted ruff,
   and `scripts/check_repo_control.py`. Do not run broad tests or contact any RPC endpoint.
6. After focused tests pass, apply migration 0018 to `dex003_full.db`, verify
   `PRAGMA foreign_key_check` is empty and all v2 acquisition tables remain empty, update the
   DEX-003 repository records, then commit and push the integration.

No acquisition, dataset publication, metadata/downstream transforms, factor design, PAPER,
or LIVE work is authorized. Return the commit hash and focused command evidence for Sol
review. Next ticket remains `NONE`.
