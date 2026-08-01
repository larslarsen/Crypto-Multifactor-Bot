# CURRENT_TASK

Ticket: DEX-003
State: IN_PROGRESS
Next required actor: Sol 5.6 High - authorize bounded v2 live matrix separately
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

Jr committed integration `741e0ba` and applied migration 0018 to `dex003_full.db`
(checksum `9acb1f1586392ced1ab9f1845906f650c5bb42eb6c9f5c487e74806821089922`).
The four authorized focused targets pass, targeted ruff passes, repository control passes,
`PRAGMA foreign_key_check` is empty, and all v2 acquisition tables remain empty.

Sol rejected the prior integration because 0018 paired acquisition/raw only for chain
identity, leaving engine events, canonical header receipts, and leaf receipts without
composite pairing FKs, and several engine tests were placeholders.

Jr applied the migration correction in follow-up commit `8bbfd0e`. Migration 0019
(`0019_uniswap_v2_pair_event_v2_engine_raw_fks.sql`) rebuilds
`uniswap_v2_pair_event_v2_engine_event`, `uniswap_v2_pair_event_v2_canonical_header_receipt`,
and `uniswap_v2_pair_event_v2_leaf_receipt` with mandatory primary and secondary composite
FKs `(acquisition_id, raw_object_id) REFERENCES raw_acquisition(acquisition_id, raw_object_id)
ON DELETE RESTRICT ON UPDATE RESTRICT`. The rebuild renames the legacy parent tables and the
leaf-header dependency table, creates the replacement tables with all preserved columns,
checks, FKs, and indexes, copies every row, and drops the legacy tables; copying any legacy
mismatched row fails atomically (migration absent from history, prior schema restored, rows
intact). Tests cover fresh apply and a populated 0018 upgrade with surviving
plan/node/header/leaf/dependency/event/raw rows and empty `PRAGMA foreign_key_check`, grouped
`PRAGMA foreign_key_list` signatures proving both pairing FKs plus exact RESTRICT actions,
primary and secondary mismatch insert rejection for event/header/leaf, delete/update RESTRICT,
and atomic rollback on an invalid legacy row. Sol accepts migration 0019 and its applied
database state. The test-only portion remains rejected because several named tests still do
not execute their promised paths: heartbeat has no claim/renewal or blocked stream; cached raw
authentication is absent; policy resume still tampers stored JSON; unsplittable logs remain
outside the singleton domain; progressed-child winner and early `_route_failure` are not
called; and normal process terminal/credential persistence are not asserted. The 142 focused
tests pass, but passing placeholders are not acceptance evidence.

0019 was applied to `dex003_full.db`: 19 migrations recorded with 0018 checksum unchanged
(`9acb1f1586392ced1ab9f1845906f650c5bb42eb6c9f5c487e74806821089922`), `PRAGMA
foreign_key_check` is empty, all 548,721 raw_acquisition and 509,711 raw_object rows are
preserved, all v2 acquisition tables remain empty, and the three rebuilt tables carry the
composite pairing FKs.

The test-only follow-up replaces the rejected placeholder tests with paths that actually
execute their promises. Heartbeat now creates a real claim, holds a multi-chunk raw stream
behind thread events, renews the lease while persistence is blocked, and asserts the renewal
advances `expires_at` before the persistence future completes. Policy resume uses a second
engine on the same plan with a changed `http_timeout_seconds` and, parametrically, changed
`command_offer_timeout_seconds`, rejecting each without mutating the stored policy row. Cached
chain and cached header replay tamper one complete-success metadata field (`truncated`, status)
and one canonical raw identity (file bytes, `storage_uri`), then re-run the public load path
and fail closed (`cached chain identity load failed` / `retry:authentication`). The unsplittable
fixture puts both unique logs and the required header at the singleton's exact block and
asserts the exact terminal receipt (mode, attempt, domain, recomputed receipt ID). The
process-path transport terminal asserts one receipt with exact mode, attempt, domain, and
recomputed ID. The progressed-child test commits a parent SPLIT through `process_one`,
progresses one exact child to `IN_FLIGHT`, calls the parent `resolve_winner(split_reason=...)`,
asserts `split_winner`, and compares every child ID, parent, bounds, addresses, topics, and
reason to the `split_node` output. Early-loss executes `_route_failure` with `_lease_lost`
true: a durable transport-mode winner is seeded, a max-attempt persistence candidate routes
through `_route_failure`, the winner-mode mismatch is rejected, and the candidate's failure
plus terminal-blocker events are durably inserted. Retry rollback keeps the node `IN_FLIGHT`
with unchanged attempt and the exact lease, and the pre-existing conflicting event is
byte-identical; `FAILURE_ROUTE_PRECEDENCE` is asserted as the exact accepted tuple.
Complete-truncated recovery proves persisted bytes/hash equal the retained spool and removes
both spool and journal. Credential coverage reads a live test spool journal and persisted
event/raw-acquisition JSON and proves neither endpoint nor key appears. The 0019 migration
target gains the secondary engine-event mismatch tests (raw-object and acquisition). All five
v2 targets pass 155 focused tests, targeted ruff passes, and repository control passes. Sol
accepts the complete engine integration at test-only follow-up commit `ad30bf9`; the heartbeat
path also passes five repeated runs. Accepted source and migrations 0018/0019 are unchanged.

## Governing documents

- tickets/DEX-003.md
- docs/adr/0015-data-first-dex-research-substrate.md

## Acceptance

The bounded v2 engine integration, migrations 0018/0019, applied database state, and focused
offline evidence are accepted at `ad30bf9`. No further engine source, migration, or integration
test work is authorized.

No live matrix, endurance pilot, acquisition, dataset publication, metadata/downstream
transforms, factor design, PAPER, or LIVE work is authorized by this acceptance. The next
phase requires a separate bounded Sol authorization. Next ticket remains `NONE`.
