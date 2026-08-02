# CURRENT_TASK

Ticket: DEX-003
State: IN_PROGRESS
Next required actor: Jr Dev - Hermes - one bounded live matrix under CURRENT_TASK
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
transforms, factor design, PAPER, or LIVE work is authorized by this acceptance. The
source-only harness phase authorized below does not authorize RPC execution. Next ticket
remains `NONE`.

## Authorized next phase - source only

Sol authorizes Sr Dev - Grok Build to implement only the isolated v2 provider-matrix
harness. This is a source drop for later Jr integration and offline testing. Grok may add
`src/cryptofactors/acquisition/uniswap_v2_pair_events_v2_matrix.py` and
`scripts/research/run_uniswap_v2_pair_events_v2_matrix.py`; it may not edit the accepted
v2 engine/foundation, migrations, tests, repository records, or production data. It may
not run RPC calls. No live matrix execution is authorized by this source pass.

The harness contract is frozen as follows:

- Verify the accepted registry manifest, dataset ID, parquet path, byte count, and SHA-256
  before deriving any address. Execute mode must reject caller-supplied pools, ranges,
  topics, provider organizations, or cohort ordering.
- Use anchor pool `0x3139ffc91b99aa94da8a2dc13f1fc36f9bdc98ee`. Build one ordered
  maximum cohort as the anchor followed by the lexicographically lowest 127 other accepted
  registry addresses born on or before block 10,388,500. Exactly 129 registry pools are
  eligible at that boundary. The compact-JSON ordered-array SHA-256 of the selected 128 is
  `24f5924de5560ac988a7b5623c493d53dfd470b8419cd1c4c7fcb189fdf2a86e`.
- Derive nested prefix cohorts of 1, 8, 32, 64, and 128 addresses. Their compact-JSON
  ordered-array SHA-256 values are, respectively,
  `592ed81e9c6fcde816e9096d0e7a5e9f2cc2722e7c5325178d7c219661fde751`,
  `0b9a87c4066849a798bcdf3e310dd61de86ebdb961c86203dbced29aecdd292a`,
  `e3fc4ddcd7054818814004209d48e59cebb913ace5247b6189a3e79c47dcc015`,
  `78c973533295d96130bc108f76d904903fc79d5e7b242af1b01a45c1782c57be`, and
  `24f5924de5560ac988a7b5623c493d53dfd470b8419cd1c4c7fcb189fdf2a86e`.
- Use exactly these inclusive pre-2025 ranges: sparse 10,388,500-10,393,499;
  medium 11,893,500-11,898,499; hot 16,353,500-16,358,499. Retained agreed v1
  Infura/BlockPI Swap receipts for the anchor contain 0, 3, and 18 logs. These counts
  select the ranges only and confer no v2 coverage credit.
- For each range, query each provider once per scalar `(address, topic)` for the maximum
  cohort, then derive every nested scalar union without duplicate scalar calls. Query each
  provider once for each of the 15 combined-topic batched cells. Every provider's batch
  must equal its own scalar union under log identity v2, and the two providers' scalar and
  batched unions must agree. Reject malformed, removed, duplicate, unsupported-topic,
  out-of-range, or out-of-cohort logs. Do not split a matrix request; a provider limit,
  truncation, conservative-cap hit, or oversized response makes that cell fail.
- Authenticate chain ID with both provider organizations before any log request. Retain
  every attempted response before retry or stop. Support zero-network offline replay that
  reproduces all cell decisions and report hashes from retained raw evidence.
- The logical-call ceiling is 1,568: two chain calls, 1,536 scalar calls, and 30 batched
  calls. Permit at most three retained attempts per logical call, 4,704 provider attempts,
  90 minutes wall time, 2 GiB total retained response bytes, 8 MB per response, eight
  requests/second/provider, and four in-flight requests/provider. Runtime options may only
  lower these ceilings.
- Default to plan-only/offline behavior. A future live path must require an explicit
  `--execute-live` flag plus confirmation of the computed matrix ID. Endpoints/credentials
  are runtime-only and must never enter plan identity, receipts, raw metadata, logs, reports,
  commands, or exceptions.
- Use a dedicated matrix output root and receipt state. Refuse `dex003_full.db`, the
  accepted dataset directory, accepted staged files, and all production v2 tables. Write a
  canonical plan, resumable request receipts, raw-object hashes, and an atomic final report;
  an incomplete run must remain visibly incomplete and receive no PASS.
- Report each cell's provider status, attempts, 429s, latency, response bytes, log count,
  identity-v2 digest, scalar-union digest, and equality decisions, plus global limits/high
  water marks and credential scans. PASS requires all 15 cells and offline replay to pass.
  The report may recommend but must not freeze 64, modify production configuration, grant
  v2 coverage, start endurance, or authorize full acquisition.

Immediate safety stops are chain disagreement, registry/cohort/hash drift, raw-persistence
failure, malformed or out-of-domain evidence, credential detection, or any global budget
breach. Ordinary RPC/429/size/cap failures are retained as cell failures and may continue
only while every global bound remains satisfied. Grok stops after delivering source and a
concise implementation note; the next step remains Jr integration and offline tests under a
separate Sol review. Endurance and all production acquisition remain unauthorized.

## Sol review - source drop rejected

Sol reviewed the two-file Grok source drop without RPC credentials or network calls. Targeted
ruff, repository control, and plan-only execution pass; plan-only derives matrix ID
`mtx_29211422a0ea5148c1601d39d647e916a57c3227d78026289685a6fb910901c2` and remains
non-PASS. The source is not accepted for Jr integration because offline probes confirmed:

- Concurrent equal response bodies race on one digest-derived `.tmp` path, causing a false
  `raw-persistence failure`; raw content-addressed writes are not concurrency-safe.
- The token bucket is not an in-flight limiter. Eight slow Infura calls reached provider
  high-water 8 while the configured hard ceiling was 4.
- `MatrixSafetyStop` is caught as ordinary `MatrixError` during cell evaluation, so malformed
  or out-of-domain evidence returns 15 incomplete cells instead of propagating an immediate
  safety stop.
- `load_body()` trusts the filename and accepts tampered bytes without recomputing SHA-256 or
  checking the receipt byte count.
- `data/dex003_full/store` is accepted as a matrix output root, despite the required dedicated
  isolation from the production registry store.
- Resume initializes all global counters at zero and does not authenticate prior attempts,
  requests, bodies, or cumulative retained bytes. `INSERT OR REPLACE` can overwrite attempt
  evidence.
- HTTP buffers `response.content` without a streaming bound and then retains only a silent
  8 MB prefix. Submitting all 1,566 log futures at once also means executor shutdown can keep
  issuing queued work after a safety stop.
- Offline replay writes a new final report instead of authenticating an immutable live report;
  timestamps/high-water values prevent exact report-hash reproduction, and a new incomplete
  run can leave an older PASS `report.json` in place.
- Failed/incomplete cells omit required per-provider attempts, 429s, latency, bytes, status,
  and error evidence. HTTP clients are not closed.

Grok is authorized for one source-only correction pass in exactly
`src/cryptofactors/acquisition/uniswap_v2_pair_events_v2_matrix.py` and
`scripts/research/run_uniswap_v2_pair_events_v2_matrix.py`. No other file, RPC call, test,
migration, record, Git action, or production artifact is authorized. The correction must:

1. Use a real per-provider semaphore/limiter in addition to RPS control, a bounded work queue,
   and a shared stop signal. On a safety stop, submit no new work, cancel queued work, drain and
   retain only already-started responses, then write one authenticated incomplete result.
2. Stream each response to a unique attempt spool without unbounded `response.content`.
   Content-addressed promotion must be race-safe for equal bodies. An over-cap response must
   retain and authenticate the bounded observed prefix with explicit `truncated=true` and
   observed-over-cap evidence, and it must never be usable as a successful body.
3. Make attempts append-only: no replace/upsert path may rewrite prior attempt evidence. On
   every resume/replay, validate the stored plan/matrix ID, exact logical-call catalog,
   canonical request JSON/SHA, provider/kind, contiguous attempts, terminal state, raw SHA-256,
   and raw byte count before credit. Reconstruct cumulative logical calls, attempts, retained
   bytes, 429s, and applicable high-water/budget state before new work.
4. Reject any output root equal to, inside, or containing the registry store, accepted dataset
   or staged production tree, `data/dex003_full`, or a state database containing production v2
   tables. Resolve symlinks before comparison.
5. Propagate `MatrixSafetyStop` ahead of ordinary cell exceptions. Preserve complete provider
   metrics and error classification for pass, fail, and incomplete cells; no malformed,
   duplicate, removed, unsupported-topic, out-of-domain, or unauthenticated body may become a
   cell failure or replay input.
6. Give each execution an immutable run identity. A new run must not leave an older PASS as the
   current result. Offline replay must never overwrite live evidence: authenticate the exact
   live plan, attempts, raw bodies, cell decisions, and a stable evidence/report hash that
   excludes runtime-only timestamps while retaining those timestamps as unhashed metadata.
7. Close all clients and spools deterministically. Scan every persisted/logged/error string for
   endpoint URLs and credential material, not only mapping keys or credential query-parameter
   spellings.

Grok must include concise offline reasoning for each correction and stop. No live matrix,
endurance, full acquisition, coverage credit, or production cohort freeze is authorized.

## Sol re-review - corrected source still rejected

Sol re-reviewed the corrected two-file drop using the updated local graph plus static and
offline-only probes. Targeted ruff, repository control, plan-only execution, equal-body
concurrency, provider in-flight enforcement, malformed-log propagation, raw-tamper rejection,
and production-store output rejection pass. Matrix ID remains
`mtx_29211422a0ea5148c1601d39d647e916a57c3227d78026289685a6fb910901c2`.

The correction is not accepted for Jr integration. Confirmed remaining blockers are:

- `build_plan()` rewrites the logical-call catalog before `authenticate_resume()`. An offline
  probe changed a stored request hash; the next build erased the tamper and resume passed.
- Resume iterates only expected call IDs. A persisted unknown attempt/raw body remained in the
  store but authenticated counters reported zero attempts. Missing catalogs, logical-call
  terminal state, sidecar receipts, and prior high-water are also not fully authenticated.
- Every `run()` writes an incomplete report and repoints `current_run.json` before replay loads
  the prior live report. A plan-only report is accepted as a live report when loaded directly;
  normal replay then loses that pointer and reports `live_report_authenticated=false`.
  `MatrixSafetyStop` is also swallowed by replay's broad `except MatrixError`, while matrix PASS
  does not require authenticated live evidence.
- Run IDs and run directories may be reused, reports use replacement writes, and concurrent
  processes can race the unguarded current pointer. The evidence hash excludes run identity and
  all high-water/budget counters; `report_hash` currently equals `evidence_hash` and is not
  independently authenticated.
- Live HTTP still collects chunk lists and joins them in memory before a second spool pass.
  Raw promotion occurs before cumulative retained-byte admission/receipt commit, so a budget
  stop can orphan raw evidence.
- Raw response strings are not scanned before promotion. An offline fake response containing an
  endpoint URL was persisted. Empty successful bodies and JSON-RPC envelopes missing `result`
  remain ordinary cell failures instead of immediate malformed-evidence safety stops.
- Failure/safety reports still omit complete per-provider status, observed bytes, truncation,
  and attempt evidence; deterministic closure and output-ancestor isolation remain incomplete
  in edge paths.

Grok is authorized for one final source-and-test correction in exactly the same two matrix files
plus `tests/acquisition/test_uniswap_v2_pair_events_v2_matrix.py`. No RPC call, test execution,
migration, record, Git action, engine/foundation edit, or production artifact is authorized.
The final correction must:

1. Split pure plan construction from persistence. For an existing output root, authenticate the
   immutable stored plan, byte-exact catalog including request JSON, exact expected call-ID set,
   every attempt row, logical-call state row, receipt sidecar, raw SHA/bytes, and cumulative
   counters before any write. Reject missing, extra, duplicate, non-contiguous, or terminally
   inconsistent evidence. Only a fresh empty root may create plan/catalog state.
2. Make run creation exclusive and immutable. Reject an existing run ID/directory, use
   append/exclusive report creation, and serialize or compare-and-swap current-pointer updates so
   an older process cannot restore stale PASS. Attempts and reports must bind to the execution
   run or to an explicitly authenticated resume identity.
3. Separate live execution from standalone replay. In-process zero-network replay may evaluate
   newly retained evidence before the immutable live report is sealed. Standalone replay must
   load a pre-existing complete `mode=execute_live` report before creating any replay run or
   changing any pointer; verify pointer/run/path/matrix ID, report hash, evidence hash, complete
   attempt snapshot, raw bodies, and cell decisions. Never catch `MatrixSafetyStop` as absence.
   PASS must explicitly require the applicable authenticated replay result.
4. Hash all evidence-bearing fields: run/resume identity, plan, budgets, cumulative logical calls,
   attempts, retained bytes, 429s, provider high-water, call/receipt/raw snapshot, cells, and
   replay decision. Exclude only wall-clock timestamps and elapsed duration. Define a distinct
   report hash that binds the evidence hash and verify both on replay.
5. Stream live HTTP bytes directly into the unique attempt spool; do not retain a chunk list or
   joined duplicate. Reserve worst-case retained-byte capacity before starting each request so
   every started response can be committed within the global bound, then release unused
   reservation. Promote raw and receipt/state atomically enough that neither can become orphaned
   authority after a safety stop.
6. Scan every decodable response/error string before raw promotion for any endpoint URL or
   credential form, including bearer values and key/token/password query parameters. Credential
   detection must persist only credential-free blocker metadata. Empty 2xx bodies, missing
   `result`, malformed envelopes/logs, and unauthenticated/truncated bodies are safety stops,
   never cell failures or replay inputs.
7. Preserve complete bounded provider/call metrics in PASS, fail, incomplete, and safety reports;
   close every owned resource on constructor and runtime failures; and reject output roots that
   equal, contain, or sit inside the resolved project `data/dex003_full` tree regardless of the
   supplied registry-store location.

Grok must author the offline test suite that freezes these requirements. At minimum, tests must
execute the previously failing paths for pre-write catalog tamper, missing/extra/unknown attempt
and logical-state evidence, receipt/raw tamper, cumulative resume budgets, exclusive run creation,
stale-pointer races, plan-only-as-live rejection, standalone replay ordering, replay safety-stop
propagation, PASS requiring authenticated replay, distinct evidence/report hash tamper, direct
bounded spooling, retained-byte reservation/rollback, equal-body promotion concurrency, hard
per-provider in-flight limits, endpoint/credential response rejection, malformed empty/missing-
result envelopes, complete failure metrics, output-tree isolation, and deterministic closure.
Tests may use only temporary stores and fake transports; they must not access RPC credentials,
make network calls, or mutate production data. Grok writes but does not run the tests.

Grok stops after production/test source plus concise reasoning that maps every correction to a
named test. Jr then integrates both drops and runs the frozen suite and acceptance commands; Jr
does not add or redesign tests. No live matrix or downstream phase is authorized.

## Jr integration - matrix harness source drop integrated

Jr integrated both corrected drops into `src/cryptofactors/acquisition/uniswap_v2_pair_events_v2_matrix.py`,
`scripts/research/run_uniswap_v2_pair_events_v2_matrix.py`, and the frozen offline suite
`tests/acquisition/test_uniswap_v2_pair_events_v2_matrix.py`, together with the role-separation
governance updates (AGENTS.md, DEVELOPMENT_ROLES.md, HERMES_START_HERE.md, check_repo_control.py,
and its tests). Jr added or redesigned no tests.

The frozen matrix suite passes 32/32. Targeted ruff passes on all three matrix files. Repository
control passes. An offline plan-only probe against the accepted registry store
(`data/dex003_full/store`, dataset `ds_42ce2515e226258557a06a374498547393bbc984db791c56fa19d81d7ef16d15`,
parquet SHA-256 `8e41a9fb1e1b05f126345ca0a7a9eb04792cd0e92d45406a9b5c031105d83256`) derives matrix ID
`mtx_29211422a0ea5148c1601d39d647e916a57c3227d78026289685a6fb910901c2`, identical to the frozen
contract, with anchor `0x3139ffc91b99aa94da8a2dc13f1fc36f9bdc98ee` and birth boundary 10,388,500.
Plan-only remains non-PASS by design; no RPC call was made, and no live matrix execution,
endurance, or downstream phase is authorized. Sol re-review is the next required actor.

## Sol review - Jr integration rejected at c9819c2

Sol reviewed commit `c9819c2`. The integrated scope is correct, the frozen matrix suite passes
32/32, the repository-control suite passes 17/17, targeted ruff passes, repository control
passes, and plan-only preserves the frozen matrix ID. No RPC call was made. The integration is
nevertheless rejected because passing tests do not execute several promised production paths.

Independent offline probes against the committed source confirmed that:

- changing `registry_parquet_sha256` in `plan.json` while retaining the old matrix ID is accepted;
- reserializing the catalog to noncanonical bytes is accepted despite the byte-exact contract;
- deleting one call's attempt row, logical state, and sidecar is accepted as a lower prior count;
- deleting `matrix_state.sqlite3` causes constructor-time recreation before authentication and
  the rolled-back store is accepted;
- an older run can write after a newer PASS and restore itself as `current_run` because the
  claimed CAS has no expected predecessor/generation argument; and
- an endpoint/credential string beyond the retained response cap is drained without scanning and
  the safe-looking prefix is promoted.

Additional review found incomplete live-snapshot authentication, mutable resume budgets/wall
time, non-atomic raw/row/sidecar promotion, missing attempt run-ID authentication, report hashes
that bind counts rather than the complete evidence set, and tests that assert helper shapes or
hand-written booleans instead of stale-writer, production PASS, direct HTTP, reservation-failure,
safety-report, and constructor-failure paths.

The bespoke resumable matrix state machine is retired before any live use. A 1,568-call provider
preflight does not justify a second durable scheduler beside the already accepted production v2
engine. No matrix evidence exists that requires backward compatibility.

Grok is authorized to replace, not patch, the matrix implementation and senior-authored tests in
exactly these files:

- `src/cryptofactors/acquisition/uniswap_v2_pair_events_v2_matrix.py`
- `scripts/research/run_uniswap_v2_pair_events_v2_matrix.py`
- `tests/acquisition/test_uniswap_v2_pair_events_v2_matrix.py`

The replacement contract is intentionally smaller:

1. Keep the frozen registry, cohort hashes, ranges, providers, topics, 15 cells, 1,568 logical
   calls, retry/request/byte/time/concurrency ceilings, scalar-union equality, identity-v2, and
   credential-free reporting contract above.
2. Remove SQLite, resume, `current_run`, pointer generations, mutable shared call state, and all
   compatibility code. Every live attempt uses a new exclusive run directory. An interrupted,
   failed, or incomplete run receives no PASS and is rerun from the beginning in another fresh
   directory.
3. Write one exclusive immutable plan/catalog at run start, exclusive attempt receipts and
   race-safe content-addressed raw objects during execution, then exactly one exclusive terminal
   `COMPLETE.json` or `FAILED.json`. The terminal manifest must enumerate and hash every allowed
   file; missing, extra, duplicate, changed, or path-escaping evidence fails authentication.
4. Standalone replay takes an explicit completed live run directory. It is strictly read-only for
   that directory, authenticates the terminal manifest and every plan/catalog/attempt/raw file,
   recomputes all 15 cells and the complete evidence hash, and writes any replay result only to a
   separate new output path. There is no implicit latest/current run.
5. Stream each response once into its unique bounded spool while hashing and scanning all bytes,
   including bytes beyond the retention cap and scanner chunk boundaries. Reserve retained-byte
   capacity before starting a request. Credential evidence is never persisted; truncation,
   malformed/empty/missing-result evidence, budget breach, or unauthenticated body cannot become
   successful authority.
6. Use a real per-provider semaphore plus RPS limiter and bounded submission. On safety stop,
   submit nothing new, drain only already-started responses, retain credential-free evidence, and
   seal `FAILED.json`. Close all owned clients/spools on every path.
7. Reports must include complete bounded call/provider/cell metrics and distinct evidence/report
   hashes. PASS requires dual mainnet authentication, all 15 cells PASS, and in-process
   zero-network replay of the just-sealed evidence. It grants no coverage or downstream authority.

Grok must replace the test suite with tests that execute public production paths. Required tests
include one complete 1,568-call fake live run plus explicit read-only standalone replay; exact
request-count and cohort/range assertions; missing/extra/tampered plan/catalog/attempt/raw/terminal
files; path escapes; duplicate attempts/logs; equal-body promotion races; per-provider in-flight
high-water; stop/drain behavior; reservation exhaustion; credential strings before, across, and
after the retained cap; malformed/empty/missing-result responses; truncation; provider errors and
disagreement; immutable terminal collision; incomplete-run non-PASS; full metrics; and resource
closure. Tests use only fake transports and temporary paths. Grok writes but does not run them;
Jr integrates the replacement and runs the unchanged suite.

No live matrix, endurance, production acquisition, coverage credit, or downstream work is
authorized. After eventual matrix acceptance, endurance must project full logs plus shared headers
to a target of seven days and a hard maximum of fourteen days, with at least 2x free-disk headroom;
otherwise acquisition stops for redesign.

## Sol review - fresh-run replacement rejected

Sol reviewed the uncommitted three-file fresh-run replacement. The rewrite removes SQLite,
resume, and current-pointer state; targeted ruff and repository control pass; and the 23-test
senior suite passes, including one complete 1,568-call fake run. The focused suite takes more than
two minutes because it honors production request pacing. No RPC call was made.

The source remains rejected after public-path probes confirmed:

- an HTTP-200 JSON-RPC error is stored as success, raises `MatrixCellFailure` during chain parsing,
  and leaves the run without either `COMPLETE.json` or `FAILED.json`;
- same-process replay reads cached receipts/raw, so tampering a promoted raw file is not detected;
- terminal authentication accepts a forged logical-call receipt and its unreferenced raw body;
- offline replay allows its output root to equal the live source directory; and
- generic completed-run authentication accepts a `mode=plan_only` run as a replay source candidate.

Static review additionally found that PASS is based on pre-seal cache-backed evaluation, terminal
authentication validates file hashes but not exact call/attempt/request/raw relationships,
standalone replay does not require dual chain evidence or a sealed live PASS, response bytes are
written before credential scanning and bytes after a credential hit are not scanned, wall time is
not hard across waits/HTTP, provider/call metrics are incomplete, and several tests still exercise
private helpers rather than scheduler/terminal/public CLI paths.

Grok is authorized for a bounded correction in the same three files only. It must:

1. Remove receipt/body authority caches or bypass them for every replay/authentication decision.
   Before sealing, evaluate through a read-only disk adapter that rehashes all raw and receipt
   bytes and validates the exact plan-derived call inventory.
2. Authenticate plan identity, canonical catalog bytes, receipt filename/call/attempt/run/request
   bindings, contiguous attempts, success/error semantics, referenced raw SHA/bytes, and zero
   unknown/orphan receipts/raw. Completed live runs must contain all 1,568 logical calls; generic
   authentication and standalone replay must require `mode=execute_live`, dual mainnet evidence,
   complete=true, PASS=true, and all 15 cells.
3. Reject replay output equal to, inside, or containing the live source after symlink resolution.
   Snapshot the source inventory before and after replay and fail if it changes.
4. Parse/classify JSON-RPC envelopes before an attempt becomes success. Retry bounded provider
   errors according to policy. Every exception after run creation, including `MatrixCellFailure`,
   must drain started work, close resources, and exclusively seal `FAILED.json`; no run may exit
   live execution without exactly one terminal.
5. Scan every response byte with a rolling boundary-safe scanner before writing that byte to disk,
   continue scanning drained bytes beyond the retention cap, and hash all observed bytes while
   separately hashing the retained prefix. Enforce wall time after semaphore/RPS waits and cap HTTP
   timeout by the remaining wall budget.
6. Provide exact per-call, per-provider, and per-cell metrics in all terminal reports and bind them
   in the hashes. Remove unsynchronized mutable HTTP-response tracking or protect it with a lock.

Senior tests must execute the five probes above through public APIs, plus public live scheduler
tests for provider retry/error FAILED sealing, disk tamper before in-process PASS, exact unknown/
orphan/duplicate receipt and raw rejection, source/output overlap and symlink escapes, source-tree
immutability across replay, credentials split across scanner chunks and beyond cap, hard wall-time
expiry while waiting/in HTTP, stop/drain behavior, complete terminal metrics, and CLI plan/live/
replay failure paths. Helper-only assertions do not satisfy these requirements. Grok writes but
does not run tests; Jr will integrate and execute only after Sol source acceptance.

No live matrix or downstream work is authorized.

## Sol re-review - bounded correction rejected

Sol re-reviewed the uncommitted three-file correction. The correction closes the five public
failures from the prior review: HTTP-200 JSON-RPC errors seal `FAILED.json`, pre-seal evaluation
rehashes raw evidence from disk, forged unknown receipt/raw evidence is rejected, replay output
overlap is rejected, and plan-only runs cannot authenticate as live replay sources. The senior
suite passes 29/29; targeted ruff, repository control, and diff checks pass. No RPC call was made.

The source and suite remain rejected only against requirements already frozen above:

- a public execute-live probe with `max_wall_seconds=0.05` and a blocking fake transport returned
  only after 0.573 seconds. `HttpxTransport` retains its constructor-time fixed timeout and the
  remaining-wall `BudgetTracker.http_timeout_seconds()` value is not applied to an HTTP request;
  therefore wall time is not hard while in HTTP;
- `test_stop_drain_behavior` calls private `_signal`/`_raise_if_stopped` methods and does not
  exercise bounded scheduler submission, cancellation, or draining of already-started work;
- no hard-wall test exists, and `test_credentials_split_across_scanner_chunks` supplies a single
  roughly 525-byte body to a helper that chunks at 65,536 bytes, so it does not cross a scanner
  chunk boundary;
- the replay test checks that `COMPLETE.json` still exists but does not compare the full source
  inventory before and after replay, and there is no symlink-overlap probe;
- no public CLI plan/live/replay failure-path tests exist, the JSON-RPC error test lowers retries to
  one rather than freezing bounded provider retry, and the terminal-metrics test asserts only
  broad key presence rather than exact per-call/provider/cell completeness.

Grok is authorized for one bounded correction in the same three matrix files only. Apply the
remaining wall budget to each real HTTP operation and make the frozen public-path tests above
execute the actual scheduler, streaming chunk boundary, replay inventory/symlink, exact terminal
metrics, retry, and CLI paths. This is completion of the existing contract, not a new requirement.
Grok writes but does not execute tests; Jr integrates and executes only after Sol source
acceptance.

No live matrix, endurance, production acquisition, coverage credit, or downstream work is
authorized.

## Sol review - second bounded correction rejected

Sol reviewed the new uncommitted three-file correction. It adds remaining-wall request timeouts,
locks mutable HTTP-response tracking, exercises the live scheduler stop path, crosses the real
65,536-byte scanner boundary, compares replay source inventories, resolves symlink overlap, freezes
three-attempt provider retry, and strengthens terminal metric assertions. Six of the seven new
decisive public-path tests pass. Targeted ruff, repository control, and diff checks pass. No RPC
call was made.

The correction remains rejected against the existing hard-wall, stop/drain, and CLI requirements:

- `test_cli_plan_live_replay_failure_paths` fails before exercising the CLI with
  `ModuleNotFoundError: No module named 'scripts'`, so the senior suite is not passing;
- a public execute-live streamed-response probe with `max_wall_seconds=0.05` returned after 0.522
  seconds. The remaining-wall timeout covers provider invocation/response headers, but
  `stream_to_receipt` consumes response chunks without checking the tracker deadline. Per-read
  HTTP timeouts therefore do not provide the required absolute wall bound for a slowly streaming
  response; and
- an injectable provider timeout calls `shutdown(wait=False)` on a still-running future and can
  seal `FAILED.json` before that started provider operation finishes. That is abandonment, not the
  required draining and closure of already-started work.

Grok is authorized for one narrow correction in the same three files only. Enforce the absolute
remaining wall while consuming response chunks; make timed-out injectable work cooperatively stop
and finish before terminal sealing; and load/exercise the CLI through an import path that works in
the repository test environment. Add public regression assertions for streamed wall expiry and no
active provider work at terminal return. These are direct completions of the already frozen
requirements, not new scope. Grok writes but does not execute tests; Jr integrates and executes the
unchanged drop only after Sol source acceptance.

No live matrix, endurance, production acquisition, coverage credit, or downstream work is
authorized.

## Sol review - stream-drain correction rejected

Sol reviewed the latest uncommitted correction. The CLI failure-path test now loads the executable
script by file path, timed-out cooperative provider calls finish before terminal return, and an
explicit streamed-response wall-expiry test passes. All four focused regression tests pass;
targeted ruff, repository control, and diff checks pass. No RPC call was made.

One existing stop/drain requirement remains blocking. `stream_to_receipt` starts a new daemon
thread for each blocking `next(chunks_iter)` call. When the wall expires, the caller raises and
decrements `_active_provider_ops` without stopping or joining that chunk-reader thread. A public
execute-live probe returned `FAILED` while `stream_finished_at_return=false`, even though both
`active_provider_ops()` and the terminal report claimed zero. For a real HTTP response, the caller
can also close the response concurrently while its unjoined reader remains inside `iter_bytes`.
This is abandoned started response work, not drain-before-terminal behavior.

Grok is authorized for one final narrow correction in the same source and test files. On streamed
wall expiry, cooperatively stop/close the response iterator and join its reader before decrementing
provider-operation accounting or sealing either terminal. The regression test must assert the
stream reader has finished at terminal return, not only that the counter is zero. Do not change any
other accepted behavior or scope. Grok writes but does not execute tests; Jr integrates and
executes the unchanged drop only after Sol source acceptance.

No live matrix, endurance, production acquisition, coverage credit, or downstream work is
authorized.

## Jr status - final stream-drain correction drop present

Sr Dev delivered the authorized final correction in the same three matrix files (working tree,
2026-08-01 21:44, newer than the records above). `stream_to_receipt` now starts a non-daemon chunk
reader, joins it on every path including wall expiry (stop/close the response iterator, join the
reader), and decrements provider-operation accounting and seals a terminal only after the join. The
suite includes `test_streamed_response_wall_expiry`, `test_hard_wall_timeout_during_blocking_provider_call`,
`test_cli_plan_live_replay_failure_paths`, and `test_symlink_replay_output_overlap_rejected`. The
drop is uncommitted and awaits Sol source acceptance; Jr integrates and executes the unchanged drop
only after acceptance. Next required actor is Sol 5.6 High.

## Sol source acceptance - final fresh-run correction

Sol accepts the final uncommitted correction in the three authorized matrix files. The prior
stream-drain blocker is closed: streamed reads use a non-daemon reader; wall expiry cooperatively
closes the response/iterator; the reader is joined before provider-operation accounting is
decremented or a terminal is sealed; and the public regression asserts the stream is finished at
terminal return. The five decisive scheduler, provider-wall, stream-wall, CLI, and terminal-metric
tests pass. Targeted ruff, repository control, and diff checks pass. The senior suite collects 33
tests. No RPC call was made.

Commit `5a5bfd1` is not the matrix integration: it contains only `docs/handoff/CURRENT_TASK.md` and
`tickets/DEX-003.md`. The accepted production source, CLI, and senior tests remain modified and
uncommitted. Jr is now authorized to integrate exactly these unchanged files:

- `src/cryptofactors/acquisition/uniswap_v2_pair_events_v2_matrix.py`
- `scripts/research/run_uniswap_v2_pair_events_v2_matrix.py`
- `tests/acquisition/test_uniswap_v2_pair_events_v2_matrix.py`

Jr must run the complete 33-test matrix suite, targeted ruff, repository control, and diff checks;
record exact results; then commit and push the three-file integration plus aligned DEX-003 records.
Jr must not redesign tests or production source. Sol integration acceptance is required after the
new commit is pushed.

No live matrix, endurance, production acquisition, coverage credit, or downstream work is
authorized.

## Jr integration - accepted matrix harness integrated

Jr integrated the Sol-accepted three-file drop unchanged and ran the complete acceptance command
set:

- `tests/acquisition/test_uniswap_v2_pair_events_v2_matrix.py`: 33 passed in 412.43s
  (0:06:52). The suite honors production request pacing; no RPC call was made.
- Targeted ruff: all checks passed on
  `src/cryptofactors/acquisition/uniswap_v2_pair_events_v2_matrix.py`,
  `scripts/research/run_uniswap_v2_pair_events_v2_matrix.py`, and
  `tests/acquisition/test_uniswap_v2_pair_events_v2_matrix.py`.
- Repository control: PASS.
- Diff checks: relative to the record commit, only the three matrix files and the two DEX-003
  record docs changed; no engine, foundation, migration, or other production source changed.

The integration commit contains exactly the accepted production source, CLI, and senior test
suite plus these aligned DEX-003 records. Jr added or redesigned no tests or production source.
Sol integration acceptance is the next required actor.

## Sol integration acceptance - 0002b70

Sol accepts the fresh-run matrix-harness integration at commit `0002b70`. The commit is pushed to
`origin/main` and contains the accepted production source, CLI, 33-test senior suite, and aligned
DEX-003 records. The committed matrix files match the source drop accepted above; no engine,
foundation, migration, or unrelated production file is included.

Acceptance evidence is the Jr-owned complete suite result (33/33 in 412.43 seconds), targeted ruff,
repository control, and diff checks, together with Sol's previously completed decisive scheduler,
provider-wall, stream-wall, CLI, and terminal-metric probes. Sol's redundant post-commit full-suite
rerun was aborted and is not counted as acceptance evidence. No RPC call was made.

The immutable fresh-run provider-matrix harness is accepted for DEX-003. This acceptance does not
authorize a live RPC matrix, endurance, production acquisition, coverage credit, publication, or
downstream research. The next phase requires a separate explicit bounded live-matrix authorization.

## Authorized next phase - one bounded live provider matrix

Sol authorizes Jr Dev - Hermes to execute exactly one fresh live provider matrix using the accepted
harness at `0002b70`, followed by one standalone read-only replay only if the live run is COMPLETE
and PASS. This is a validity matrix, not endurance or production acquisition. No other RPC command,
automatic retry, second live run, source edit, test redesign, migration, publication, or downstream
work is authorized.

### Preconditions

All preconditions are mandatory:

1. Jr first integrates and pushes this acceptance/authorization record without including unrelated
   staged DATA-009 or acquisition-daemon work. The three matrix files must remain byte-identical to
   commit `0002b70`.
2. Re-run the no-network plan-ID command below. It must print exactly
   `mtx_29211422a0ea5148c1601d39d647e916a57c3227d78026289685a6fb910901c2`.
3. The owner supplies `ETHEREUM_RPC_URL` at runtime for an Infura organization account and
   `ETHEREUM_RPC_URL_SECONDARY` for an independent BlockPI organization account. The owner must
   attest that the organizations are Infura and BlockPI and that the URLs are distinct. Never place
   endpoint values, keys, or tokens in commands, shell history, records, logs, or chat.
4. `data/dex003_v2_matrix/live_0002b70_mtx_29211422` and
   `data/dex003_v2_matrix/replay_0002b70_mtx_29211422` must not already exist or resolve through a
   symlink. Do not delete, reuse, or overwrite any prior run to satisfy this precondition.
5. At least 4 GiB must remain free on the output filesystem. Sol observed 439,430,504,448 bytes free
   before authorization. Both endpoint variables are currently unset in Sol's shell, so execution
   cannot begin there without owner-supplied runtime injection.
6. Do not run the matrix alongside tests, acquisition daemons, backfills, or another high-load job.

### Authorized commands

No-network plan verification:

```bash
uv run python scripts/research/run_uniswap_v2_pair_events_v2_matrix.py \
  --registry-store-root data/dex003_full/store \
  --print-matrix-id
```

After every precondition passes, the one authorized live command is:

```bash
uv run python scripts/research/run_uniswap_v2_pair_events_v2_matrix.py \
  --registry-store-root data/dex003_full/store \
  --output-root data/dex003_v2_matrix/live_0002b70_mtx_29211422 \
  --execute-live \
  --confirm-matrix-id mtx_29211422a0ea5148c1601d39d647e916a57c3227d78026289685a6fb910901c2 \
  --max-logical-calls 1568 \
  --max-attempts-per-call 3 \
  --max-provider-attempts 4704 \
  --max-wall-seconds 5400 \
  --max-retained-response-bytes 2147483648 \
  --max-response-bytes 8388608 \
  --requests-per-second 2 \
  --max-in-flight 2 \
  --http-timeout-seconds 60
```

The reduced 2 requests/second/provider and 2 in-flight/provider limits isolate filter validity from
quota pressure and reduce workstation load; the immutable 1,568-call plan, three-attempt policy,
90-minute wall, 2 GiB retained-byte cap, and 8 MB response cap remain frozen. Runtime options must
not be raised or otherwise changed.

If and only if the live summary reports COMPLETE and PASS, copy its credential-free `run_dir` value
into `LIVE_RUN_DIR` and execute one standalone replay to the separate fresh output root:

```bash
uv run python scripts/research/run_uniswap_v2_pair_events_v2_matrix.py \
  --registry-store-root data/dex003_full/store \
  --output-root data/dex003_v2_matrix/replay_0002b70_mtx_29211422 \
  --offline-replay \
  --live-run-dir "$LIVE_RUN_DIR"
```

### Immediate stops

Any missing/mismatched precondition, nonzero live exit, `FAILED.json`, missing terminal, safety stop,
chain disagreement, registry/cohort/matrix-ID drift, malformed or out-of-domain evidence,
credential detection, provider disagreement, truncation, response/cumulative budget breach, or any
cell other than PASS stops the phase. Preserve the entire immutable run directory. Do not clean it,
edit it, replay a failed source, change limits/providers, or start another live run. Return evidence
to Sol for review.

### Required evidence

Jr records only credential-free evidence: integration/authorization commit, matrix ID, live run ID
and path, terminal kind, exit code, elapsed time, all 15 cell statuses, logical/provider attempt
counts, retained/observed bytes, 429s, in-flight high-water, evidence hash, report hash, output bytes,
remaining free disk, and any blocker class. For PASS, also record the standalone replay run ID/path,
exit code, authenticated live evidence/report hashes, all-cell decision, and source-inventory hash.
Never record endpoint values or command environments.

Matrix PASS does not freeze cohort 64 or any other cohort and does not authorize endurance. Sol must
review the immutable live and replay evidence and issue a separate endurance decision. Full event
acquisition, headers, metadata, publication, factors, PAPER, and LIVE trading remain prohibited.
