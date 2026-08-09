# CURRENT_TASK

Ticket: DEX-003
State: IN_PROGRESS
Next required actor: Jr Dev - Hermes - publish Sol eleventh production-foundation correction rejection
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

## Jr evidence - bounded live matrix COMPLETE but NOT PASS

Jr executed the one authorized live matrix from the accepted harness at `0002b70` with the frozen
runtime options (2 requests/second/provider, 2 in-flight/provider, 1,568 logical calls, 3 attempts
per call, 90-minute wall, 2 GiB retained cap, 8 MB response cap) on 2026-08-02T19:11Z, matrix ID
`mtx_29211422a0ea5148c1601d39d647e916a57c3227d78026289685a6fb910901c2`.

**Incident disclosure - two concurrent live runs (Jr procedural error):** the first launch detached
via `setsid`; `setsid` forked a child whose PID differed from the recorded wrapper PID, so the
wrapper appeared dead while the real process survived in a new session and kept running. Believing
the first run had been killed, Jr launched a second live run in the foreground. Both processes then
ran concurrently from 19:13:48Z until the first finished at 19:29:51Z. This violates the
one-live-run precondition and the concurrent-run precondition. Both immutable run directories are
preserved unmodified as evidence.

Run A (setsid survivor) - `run_5ed38a9ada6942d5964eeb622963d2d5`:
- started 2026-08-02T19:11:23Z, finished 19:29:51Z (~18.5 min), status COMPLETE, `pass=false`.
- cells 5 pass / 10 fail; logical calls started 1,568; provider attempts 1,988; 429s 451;
  retained response bytes 141,370,620; in-flight high-water 2; credential scan pass.
- evidence hash `db083430a7ac7af27258eb8f5087c11d9a40c899312a578da4187661e869a115`; report hash
  `970639d0e0d6d4a879844f87d6693aee8c14c556934b5c765d76e5ecdb29e43b`; output bytes 95,312,242.

Run B (foreground) - `run_70e886dd31674d259042d11ac4194763`:
- started 2026-08-02T19:13:48Z, finished 19:32:05Z (~18.3 min), exit code 1, status COMPLETE,
  `pass=false`.
- cells 7 pass / 8 fail; logical calls started 1,568; provider attempts 1,942; 429s 411;
  retained response bytes 144,864,686; in-flight high-water 2; credential scan pass.
- evidence hash `dbd4591046b72783854e2ca2f90703c78f1d1f57f0e07774c9e481d7bcee121d`; report hash
  `69863959d13254a69dbc4b49975f21c0a14035f3c28ec598f70b8e5770712b1f`; output bytes 98,753,821.

Common blockers (both runs): `credential_detection` on several Infura scalar calls (scan matched
endpoint/credential patterns in provider responses for pools such as
`0x05556053d0966c7701201a2103dcb56cf75bdd92` (sparse sync), `0xed049cb4d4a4ee4b7e124297871c452036dfb881`
(hot swap), and `0x2cf500dccf4b8f68126ed155acd351aad8b328fe` (medium sync)); plus
`provider_limit_or_size` / `body_size_pressure` on both providers for medium-cohort cells. Both runs
report `credential_scan: pass` (no credentials persisted).

No standalone replay was run: PASS is a hard precondition for replay, and neither run is PASS. No
other live run is running or retained. Free disk after the runs: 433,185,316,864 bytes. The phase
stops here per the immediate-stop contract; the evidence above is returned to Sol for review.

## Sol evidence review - capacity redesign required

Both COMPLETE non-PASS run directories authenticate as credential-free, read-only evidence. The
Infura `credential_detection` cell failures are false positives from scanning safe generic endpoint
text as if it were a credential. Medium cohort 32 is nevertheless reproducibly nonviable under the
frozen limits: Infura returned provider-limit responses and BlockPI exceeded the 8 MiB response cap.
The live results therefore do not support cohort 64 and do not authorize replay or endurance.

ADR-0015 now selects the largest universally viable nested prefix rather than requiring every tested
cohort to pass. Every scalar reference must succeed and agree across providers. Larger authenticated
capacity failures may bound the selection; quota exhaustion, authentication/credential failure,
malformed evidence, provider disagreement, successful digest mismatch, and nonmonotonic viability
remain hard blockers. Authentication and replay must recompute the recorded selection. A fresh live
root also requires an OS-backed exclusive lock. Any future live confirmation requires separate Sol
authorization and is capped at 0.5 requests/second/provider and one in-flight request/provider.

An incomplete third start is also retained as incident evidence at
`run_32d7c4d9fdc0406f90c768f179663c5a`: 240 provider attempts and 124 Infura 429s, with no terminal.
It is not capacity-selection evidence and must not be resumed, replayed, deleted, or overwritten.

## Artifact-loss incident - prior source acceptance withdrawn

After Sol reviewed and accepted an uncommitted matrix capacity-selection correction, Jr ran
`git reset --hard HEAD` at `cbf5493`. That destructive reset removed the accepted production-source,
senior-test, ADR, and record edits. The current matrix source, CLI, and tests are byte-identical to
the accepted `0002b70` baseline; the baseline has 33 tests and does not implement section 9.8.

No source Git object, stash, temporary backup, or ZIP contains the lost correction. Pre-reset `.pyc`
files are evidence that a newer implementation and expanded suite existed, but decompilation cannot
reproduce an unchanged accepted source drop and is not authorized. The previous source acceptance
is withdrawn because its artifact is unavailable, not because the reviewed design was rejected.
There is no Jr integration authorization and no live RPC authorization.

Sr Dev - Grok Build is authorized for one bounded recovery drop in exactly:

- `src/cryptofactors/acquisition/uniswap_v2_pair_events_v2_matrix.py`
- `tests/acquisition/test_uniswap_v2_pair_events_v2_matrix.py`

The CLI remains unchanged. Sr should redeliver its exact prior source and tests if they remain in its
own context. If exact redelivery is unavailable, Sr must clearly label the result a fresh regeneration
from committed baseline `0002b70` implementing ADR-0015 section 9.8 and the following previously
reviewed requirements: exact runtime credential detection without rejecting safe generic URLs;
Bearer and secret-query-form detection; fair provider scheduling; scalar agreement before batch
evaluation; successful digest mismatch as a hard blocker; deterministic largest-universally-viable
nested-prefix selection; authenticated COMPLETE non-PASS evidence; recomputation of
`capacity_selection` during generic authentication and replay; and an OS-backed exclusive live-root
lock. The expanded senior suite must retain the prior 46-test collection and cover these behaviors.

Sr writes but does not execute tests, edit records, use decompiled output as source, run RPC, or
commit. Sol must perform a fresh source review because the lost drop has no recorded source hash.
Fresh source acceptance must record SHA-256 digests for both authorized files. Only after Sol source
acceptance may Jr verify those digests, integrate the unchanged recovery drop, execute tests and
controls, update records, commit, and push. Jr must not run destructive reset, clean, or checkout
commands while the recovery drop is uncommitted. Replay, live confirmation, endurance, production
acquisition, coverage credit, publication, factors, PAPER, and LIVE trading remain prohibited.

## Sol source review - regenerated recovery drop rejected

Sr delivered a fresh regeneration in the two authorized files. It is not accepted for Jr
integration. Reviewed file identities are:

- production source SHA-256
  `aa96a46b8184a35cedb574327be9ef81b6d75d023ab3771b9022435f2d0050cb`
- senior tests SHA-256
  `cad89db604975d64f5d83e12005fd7ea09c03d84df5d90b710ff58f2f7707cd8`

The OS-backed live-root lock is acquired before run creation and fair scheduling is present, but the
drop has blocking validity and isolation defects:

1. Generic COMPLETE authentication recomputes `capacity_selection` only from sealed report cells,
   not retained receipts/raw bodies. A report can therefore authenticate mutually consistent forged
   cells and selection that contradict disk evidence. The new COMPLETE non-PASS test constructs and
   accepts exactly that contradiction.
2. `_batch_digest` maps every unsuccessful batch to `batch call has no successful body`, which is a
   capacity marker before receipt metrics are examined. HTTP 429, quota, authentication, and other
   blocking failures can therefore be accepted as larger-cohort capacity boundaries. Batch
   evaluation also stops after the first provider failure, so one apparent capacity failure can hide
   the other provider's blocker.
3. Capacity selection does not validate the canonical 15-cell topology. Duplicate or unknown ranges
   can replace required sparse/medium/hot cells while still producing a valid selection.
4. Credential scanning uses mutable process-global `_ACTIVE_SCANNER` state. A concurrent plan/replay
   harness or live harness on another root can clear or replace a live run's scanner. Plain `key=`
   query credentials are omitted, a fixed 512-byte tail can miss longer exact values crossing stream
   chunks, and treating any long final endpoint path segment as a secret can reject safe generic
   URLs.
5. The recovery tests are predominantly helper-level. They do not prove raw-versus-sealed rejection
   in generic authentication, public live selection of cohort 8, quota/auth/credential/malformed
   hard blocking, production scheduler fairness, runtime scanner wiring, or cross-process lock
   ownership through terminal sealing.

Sr Dev is authorized for one bounded correction in the same two files only. The correction must:

- recompute canonical cells and capacity selection from authenticated retained evidence during every
  generic execute-live COMPLETE authentication, including `pass=false`, and compare both to the
  sealed report;
- validate exactly one canonical cell for each sparse/medium/hot and 1/8/32/64/128 combination, with
  exact canonical `cell_id`, rejecting duplicates, omissions, and unknown topology;
- derive capacity only from explicit retained provider-limit/body-size evidence; inspect both
  provider outcomes independently; and hard-block any quota/429, authentication, credential,
  malformed, disagreement, successful digest mismatch, ambiguous failure, or nonmonotonic result;
- replace process-global scanner ownership with scanner state bound explicitly to the live harness or
  run, without plan/replay cross-talk; detect exact runtime endpoints and actual extracted secrets,
  Bearer forms, and `key`/`api_key`/token/password/secret query forms across stream boundaries and
  beyond the retention cap while allowing credential-free generic URLs;
- retain the OS-backed canonical-root lock and prove in a subprocess that contention fails before run
  creation while the first live harness owns the lock through terminal sealing;
- add public-path regressions for cohort-8 selection, generated COMPLETE non-PASS authentication,
  raw-versus-sealed mismatch, each hard-blocker class, runtime scanner behavior, and actual scheduler
  submission fairness. Do not remove prior tests; collection may exceed 46.

Sr writes but does not execute tests, RPC, records, Git, or commits. Sol must re-review and record new
SHA-256 identities before any Jr integration. The current record edits and recovery drop remain
uncommitted; no destructive Git command is permitted. All live and downstream prohibitions remain.

## Sol source re-review - corrected recovery drop still rejected

The correction closes the prior raw-versus-sealed authentication defect, canonical 15-cell topology,
process-global scanner ownership, independent dual-provider batch evaluation, public cohort-8 path,
and public scheduler-path coverage. It remains unaccepted. Reviewed file identities are:

- production source SHA-256
  `9a8aec01182807ffa79e6ae7de01bb729a6d5837f1e8fad32459f13673adc0be`
- senior tests SHA-256
  `fce903747b403b49b2673d2f0e85d9cd7b3fda0101805ab8f38b06801b6ef433`

Remaining blockers:

1. Batch classification uses only the final attempt's `error_class`. A retained earlier 429,
   authentication failure, credential failure, or ambiguous blocker followed by a final
   provider-limit response can become capacity. Explicit cumulative `http_429s` is recorded but not
   used for the cell decision. Every retained attempt must participate and any hard blocker must
   dominate later capacity or success evidence.
2. Any JSON-RPC error containing the generic word `timeout` is mapped to
   `provider_limit_or_size`. An ambiguous timeout is not explicit provider-limit/body-size evidence
   and must hard-block; only an authenticated provider message that explicitly identifies result or
   body-size capacity may establish a boundary.
3. Execute-live still permits an injected transport with no RPC URLs or explicit scanner secrets,
   leaving no exact runtime endpoint/secret needles. An injected live transport must provide the same
   scanner inputs as the HTTP transport or execution must fail before run creation.
4. Secret extraction still treats any long path tail following generic `v1`/`v2`/`v3`/`rpc` path
   segments as a credential. Restrict path-secret extraction to the frozen provider-specific endpoint
   forms; generic credential-free path slugs must remain allowed. Full configured endpoint matching,
   userinfo, sensitive query values, and explicit extra secrets remain mandatory.
5. The public runtime-scanner test only asserts that the secret is absent from the returned report;
   it does not prove `credential_detection`, absence of secret-bearing raw authority, generated
   COMPLETE non-PASS authentication, or concurrent plan/replay isolation. The subprocess lock test
   directly calls the lock while the owner is mid-transport, not a competing public harness while the
   owner is blocked inside terminal sealing. Scheduler fairness only requires both providers somewhere
   in the first eight calls rather than round-robin or prefix imbalance at most one.

Sr Dev is authorized for one final narrow correction in the same two files. It must aggregate and
classify all retained attempts for each scalar and batch logical call, with any quota/429,
authentication/authorization, credential, malformed, transport, or ambiguous failure hard-blocking
selection even if another attempt is capacity-classified or successful. Remove generic timeout from
capacity markers unless the provider message explicitly states a result/body-size limit. Require
explicit scanner inputs for every injected execute-live transport and limit path-tail secret extraction
to the frozen Infura and BlockPI endpoint forms.

Add decisive regressions for mixed-attempt and mixed-provider precedence; HTTP 401/403; ambiguous
timeout versus explicit size limit; injected transport without scanner inputs; generic `/v3/` path
slug allowance; public live credential detection with no secret-bearing raw authority; a
production-generated COMPLETE non-PASS terminal authenticated generically and rejected for PASS
replay; concurrent plan/replay scanner isolation; a competing subprocess public harness during a
blocked `MatrixRun.seal`; and scheduler prefix imbalance no greater than one. Independently exercise
topology omission, unknown range/size, and mismatched `cell_id` branches.

Sr writes but does not execute tests, RPC, records, Git, or commits. Sol must re-review and record new
SHA-256 identities before Jr integration. No destructive Git command is permitted while this drop and
the records remain uncommitted. All live and downstream prohibitions remain.

## Sol final source review - narrow correction still required

The latest correction closes batch attempt-history precedence, 401 handling in source, ambiguous
timeout classification, injected-transport scanner inputs, provider-specific path-tail extraction,
runtime credential raw-authority rejection, generated COMPLETE non-PASS authentication, blocked-seal
lock ordering in source, and independent topology branches. It remains unaccepted. Reviewed identities:

- production source SHA-256
  `56e10a7f61da9d17c3612f7bea4ac22fa3b1d77ef69fa8e13b7d835f1d782044`
- senior tests SHA-256
  `ee3c9952b94d3d4d8f2dc895ec282eebdbaea15cee7542d2acd0c5eda5d4dbe1`

One production validity defect remains. Scalar providers are evaluated sequentially. If the first
provider has no successful scalar body but its retained failures are capacity-classified, that
capacity class is propagated to the cell and the second provider is not evaluated. Every scalar
reference is mandatory: no successful scalar body is always a hard `scalar_failure`, never a capacity
boundary, and both providers' complete scalar attempt histories must be inspected independently so
one provider cannot hide the other's quota, authorization, credential, malformed, transport, or
ambiguous blocker.

Several decisive regressions are also incorrect or incomplete:

- the generic `/v3/` test scans the exact configured runtime endpoint while expecting it to pass;
  the exact endpoint must fail, while the same generic slug at a different URL must pass;
- the subprocess contender cannot reach lock acquisition because the parent-only plan monkeypatch is
  absent in the child and the child registry fixture is empty;
- the scanner-isolation test is sequential plan/live and never runs offline replay;
- the 401/403 test exercises only 401, and mixed-provider hard-block dominance is absent;
- scheduler fairness observes nondeterministic worker-entry order rather than deterministic submission
  order; and the generated non-PASS test performs an unused first full fake-live run.

Sr Dev is authorized for one strictly bounded correction in the same two files. Implement independent
scalar-side evaluation analogous to batch-side evaluation; aggregate every retained scalar attempt;
require a success body from both providers; and make any no-success scalar side a hard
`scalar_failure`, with stronger hard blockers retaining precedence. Add one mixed-provider scalar and
batch precedence regression.

Correct the generic-path test to distinguish a forbidden exact configured endpoint from an allowed
credential-free URL carrying the same slug. Make the subprocess public contender reach the lock by
providing a valid child plan/registry path or applying an equivalent child-local plan fixture. Run a
real concurrent plan and offline replay while a separate live scanner is active. Exercise HTTP 403
separately. Observe executor submission order, not concurrent transport-entry order, and assert every
submission prefix has provider imbalance at most one. Remove the unused first execute-live run from
the generated non-PASS test. Do not add further scope.

Sr writes but does not execute tests, RPC, records, Git, or commits. Sol must re-review and record new
SHA-256 identities before Jr integration. No destructive Git command is permitted. All live and
downstream prohibitions remain.

## Jr full-suite evidence - one credential marker failure

Jr verified the accepted hashes remained unchanged and ran the complete matrix test file. The log at
`logs/dex003/matrix_suite_full_run.log` reached 100% with one failure:
`test_authorization_detail_with_credential_material_classifies_credential` at test line 2572.

The actual persisted `error_detail` was `credential_or_endpoint_detected`; the accepted test requires
the canonical credential-free marker `redacted_credential_or_endpoint`. Classification remained
`credential_or_endpoint`, and no endpoint or secret was persisted. This is not a false PASS or secret
leak, but it violates the frozen receipt taxonomy and the accepted regression.

The source acceptance is withdrawn and Jr must not commit or push. Sr Dev - Grok Build is authorized
for one literal-normalization correction in the production source only, with the senior test retained
unchanged. Every scanner-detected credential path, including streamed response-body detection and
error-detail detection, must persist `error_class=credential_detection` and
`error_detail=redacted_credential_or_endpoint`. Do not change classification, scanner behavior, tests,
or any other source.

Sr writes but does not execute tests, RPC, records, Git, or commits. Sol must review and hash the
source correction before Jr may rerun the single failure and then the complete suite. All live and
downstream prohibitions remain.

## Sol source acceptance - canonical credential marker

Sol accepts the literal source correction. Accepted identities are:

- production source SHA-256
  `9f84dd007264372ed6499ba3782c0bb34ae0b83090acbf6ed31ff62d715d6a42`
- unchanged senior tests SHA-256
  `afef397a02ee651542678f19d87f0c01ee55cd21f24d27e67056ca5bbdb6e2f8`

Every scanner-detected credential path now persists `error_class=credential_detection` and the single
canonical credential-free detail `redacted_credential_or_endpoint`. The obsolete
`credential_or_endpoint_detected` marker is absent. Classification, scanner behavior, and tests are
otherwise unchanged. Targeted ruff, repository control, and diff checks pass; Sol ran no pytest or
RPC.

Jr must verify both hashes, rerun only
`test_authorization_detail_with_credential_material_classifies_credential`, and stop with its exact
log if it fails. If it passes, Jr must rerun the complete matrix test file, targeted ruff, repository
control, and diff checks; record exact pass count and duration; and verify both hashes remain unchanged.
If all pass, commit and push only the accepted source/test and three aligned DEX-003 record files. Do
not include the unrelated `research/sprint_004/52_GMGN_SOLANA_DEX_PROSPECTIVE.md` file and do not use
destructive Git commands.

Replay, live confirmation, endurance, production acquisition, coverage credit, publication, factors,
PAPER, and LIVE trading remain prohibited. Sol integration acceptance is required after the push.

## Jr test evidence - accepted recovery drop fails authorization regressions

Jr verified that the accepted production and test hashes remained unchanged, then ran a two-test
targeted command recorded at `logs/dex003/matrix_suite_failures.log`. This was not the complete matrix
suite. Pytest collected two tests and both failed in 22.58 seconds:

- `test_http_401_is_hard_blocker`
- `test_http_403_is_hard_blocker`

Both expected `failure_class=blocking_failure`. Sol reproduced the 401 case only with local-variable
output: one failed in 10.93 seconds, no network or RPC. Disk evaluation showed every cell as
`failure_class=credential_or_endpoint`, with retained batch error classes still `http_401`.

The root cause is deterministic. `MatrixRun.retain_bytes` pre-redacts any nonempty error detail whose
text merely contains `http`, converting ordinary `HTTP_401` and `HTTP_403` details to
`redacted_credential_or_endpoint`. `_classify_one_attempt_row` then checks credential text before the
explicit 401/403 status, misclassifying authorization failures. Selection remains hard-blocked, so
this defect cannot create a false PASS, but it corrupts the required evidence taxonomy and fails the
accepted senior regressions.

The prior source acceptance is withdrawn. Jr must not edit tests, continue the suite, commit, or push.
Sr Dev - Grok Build is authorized for one narrow correction in exactly the existing production source
and senior-test files. Ordinary HTTP status details must not be treated as credential evidence merely
because they contain `http`. Preserve exact runtime endpoint/secret protection by using the actual
per-run scanner; when that scanner detects credential material in an error detail, record
`credential_detection` and redact the detail. Explicit status 401/403 without detected credential
material must classify as `blocking_failure`. Retain both existing 401/403 regressions and add or
strengthen one credential-bearing authorization-detail regression proving real credential material
still classifies as `credential_or_endpoint` and is not persisted.

Sr writes but does not execute tests, RPC, records, Git, or commits. Sol must review the correction and
record new SHA-256 identities before Jr receives another integration/test authorization. Replay, live
confirmation, endurance, production acquisition, coverage credit, publication, factors, PAPER, and
LIVE trading remain prohibited.

## Owner confirmation - prior live evidence lost

The owner confirms that all three prior immutable run directories were lost. Their committed
credential-free summaries and hashes remain incident audit records, but the underlying responses,
receipts, and terminal files can no longer be authenticated or replayed. The prior runs receive no
capacity-selection, replay, endurance, or coverage credit. A fresh run is new evidence and cannot
retroactively replace the lost historical evidence.

## Authorized next phase - one fresh live confirmation at 90c4082

Sol authorizes Jr Dev - Hermes to publish this integration-acceptance/evidence-loss record and then
execute exactly one fresh live provider-matrix confirmation from the accepted source at `90c4082`.
One standalone read-only replay is conditionally authorized only if that live run is COMPLETE and
PASS. No retry, second live run, detached process, source/test edit, endurance, or production
acquisition is authorized.

### Preconditions

1. Jr first commits and pushes only `docs/handoff/CURRENT_TASK.md` and `tickets/DEX-003.md`; exclude
   the unrelated untracked GMGN research draft. The committed source/test hashes must remain exactly
   `9f84dd007264372ed6499ba3782c0bb34ae0b83090acbf6ed31ff62d715d6a42` and
   `afef397a02ee651542678f19d87f0c01ee55cd21f24d27e67056ca5bbdb6e2f8`.
2. Re-run the no-network matrix-ID command. It must print exactly
   `mtx_29211422a0ea5148c1601d39d647e916a57c3227d78026289685a6fb910901c2`.
3. The owner supplies distinct runtime URLs for Infura and BlockPI through
   `ETHEREUM_RPC_URL` and `ETHEREUM_RPC_URL_SECONDARY`. Never persist or display either value.
4. Neither `data/dex003_v2_matrix/live_90c4082_mtx_29211422` nor
   `data/dex003_v2_matrix/replay_90c4082_mtx_29211422` may exist or resolve through a symlink. Do not
   delete or reuse another directory to satisfy this precondition.
5. At least 8 GiB must remain free on the data filesystem. Sol observed 192,001,794,048 bytes free.
6. No tests, daemon, backfill, acquisition, or other high-load job may run concurrently. Execute in
   the foreground only: no `setsid`, `nohup`, shell backgrounding, terminal multiplexer detachment, or
   automatic restart.

### Authorized commands

No-network identity check:

```bash
uv run python scripts/research/run_uniswap_v2_pair_events_v2_matrix.py \
  --registry-store-root data/dex003_full/store \
  --print-matrix-id
```

After every precondition passes, the sole authorized live command is:

```bash
uv run python scripts/research/run_uniswap_v2_pair_events_v2_matrix.py \
  --registry-store-root data/dex003_full/store \
  --output-root data/dex003_v2_matrix/live_90c4082_mtx_29211422 \
  --execute-live \
  --confirm-matrix-id mtx_29211422a0ea5148c1601d39d647e916a57c3227d78026289685a6fb910901c2 \
  --max-logical-calls 1568 \
  --max-attempts-per-call 3 \
  --max-provider-attempts 4704 \
  --max-wall-seconds 5400 \
  --max-retained-response-bytes 2147483648 \
  --max-response-bytes 8388608 \
  --requests-per-second 0.5 \
  --max-in-flight 1 \
  --http-timeout-seconds 60
```

If and only if the live terminal is COMPLETE and PASS, use its credential-free `run_dir` as
`LIVE_RUN_DIR` and run exactly one standalone replay:

```bash
uv run python scripts/research/run_uniswap_v2_pair_events_v2_matrix.py \
  --registry-store-root data/dex003_full/store \
  --output-root data/dex003_v2_matrix/replay_90c4082_mtx_29211422 \
  --offline-replay \
  --live-run-dir "$LIVE_RUN_DIR"
```

### Stops and evidence

Any failed precondition, nonzero live exit, FAILED or missing terminal, safety stop, credential
detection, quota exhaustion, malformed/incomplete evidence, provider disagreement, digest mismatch,
nonmonotonic viability, budget breach, or invalid capacity selection stops the phase. Preserve the
entire output tree; do not edit, delete, resume, replay, or rerun it. A COMPLETE non-PASS run may be
authenticated for review but is not replay-authorized.

Jr returns only credential-free evidence: record commit, source/test hashes, matrix/run IDs, terminal
kind, exit code, duration, all 15 cells, capacity selection, logical/provider attempts, 429s, retained
and observed bytes, in-flight high-water, evidence/report hashes, output bytes, free disk, and blocker
class. For conditional replay also record replay run/path, exit, authenticated source hashes, selected
cohort, all-cell decision, and source-inventory hash. No live result authorizes endurance or production.

## Sol authorization-classification review - credential precedence correction required

The correction closes the observed failures: ordinary retained HTTP 401 and 403 details are no longer
broadly redacted, classify as `blocking_failure`, and remain hard blockers. Actual per-run scanner hits
in authorization details are persisted as `credential_detection` with redacted detail and no secret
raw authority. Reviewed identities:

- production source SHA-256
  `27af4432a10d624821d9aead30b12237cd9d875951ec7e284d7d052fff17b5d3`
- senior tests SHA-256
  `ac49cc097ba6cfcdd7068a595a03bd26af363ebdd3be2115986f7b5ccc259f69`

One precedence blocker remains. `_classify_one_attempt_row` checks `http_429` before the persisted
`credential_detection` error class. A response containing real detected credential material while
also carrying HTTP 429 is therefore demoted to `quota_or_429`, contrary to the frozen hard-blocker
precedence and the retained receipt taxonomy.

Sr Dev is authorized for one final one-ordering correction in the same source/test files. A persisted
`credential_detection` class must return `credential_or_endpoint` before evaluating 429, status, or
capacity markers. Preserve ordinary 401/403 behavior. Add one mixed credential-plus-429 regression
that passes actual scanner-detected endpoint/secret material through receipt persistence, proves the
cell class is `credential_or_endpoint`, and proves no secret is retained. Do not change other source or
tests.

Sr writes but does not execute tests, RPC, records, Git, or commits. Sol must review and hash the
correction before Jr authorization. All live and downstream prohibitions remain.

## Sol source acceptance - authorization precedence correction

Sol accepts the current uncommitted recovery drop for Jr integration and test execution. Accepted
identities are:

- production source SHA-256
  `af7c1a24d283809ca2a9235133d83116d2ce4bb939a35a86198aa244bd9d05d0`
- senior tests SHA-256
  `afef397a02ee651542678f19d87f0c01ee55cd21f24d27e67056ca5bbdb6e2f8`

Persisted `credential_detection` now maps to `credential_or_endpoint` before 429, authorization, and
capacity checks. The new mixed regression passes actual scanner-detected endpoint material through
receipt persistence with `http_429=true`, verifies credential classification and redaction, and proves
the endpoint/secret is absent from receipts and raw objects. Ordinary secret-free HTTP 401/403 remains
`blocking_failure`.

Targeted ruff, repository control, and diff checks pass. The senior file contains 74 visible test
functions. Sol did not run pytest or RPC for this correction.

Jr must first verify both accepted hashes and execute only these three regressions:

- `test_http_401_is_hard_blocker`
- `test_http_403_is_hard_blocker`
- `test_credential_detection_precedes_http_429_classification`

If any gate test fails, stop without source/test edits, commit, or push and return the exact log. If all
three pass, run the complete matrix test file, targeted ruff, repository control, and diff checks;
record exact collection/pass count and duration; and verify both accepted hashes remain unchanged.
Then commit and push only the accepted source/test files and the three aligned DEX-003 records. Do not
use destructive reset, clean, or checkout commands.

Replay, live confirmation, endurance, production acquisition, coverage credit, publication, factors,
PAPER, and LIVE trading remain prohibited. Sol integration acceptance is required after the push.

## Sol source acceptance - recovered capacity redesign

Sol accepts the current uncommitted production-source and senior-test recovery drop for Jr
integration. Accepted identities are:

- `src/cryptofactors/acquisition/uniswap_v2_pair_events_v2_matrix.py` SHA-256
  `1782779e6fd9e99f60565568500271adf5313c5625029cecb21b70b1978ad5bb`
- `tests/acquisition/test_uniswap_v2_pair_events_v2_matrix.py` SHA-256
  `283b3029ec4c94f89239507b15d8436327f1e40ad5157b5afcac8df5c8478d74`

The accepted source now recomputes canonical cells and capacity selection from retained evidence;
authenticates COMPLETE non-PASS evidence; enforces canonical cell topology; evaluates both providers'
complete scalar and batch histories; separates incomplete evidence from blocker classification;
hard-blocks quota, authorization, credential, malformed, transport, ambiguous timeout, disagreement,
and successful digest mismatch; permits only explicit provider result/body-size capacity boundaries;
uses per-run exact credential scanners; fairly schedules providers; and holds an OS-backed canonical
root lock through terminal sealing. Missing scalar evidence seals FAILED, and raw-integrity safety
stops are not demoted to cell failures.

Targeted ruff, repository control, and diff checks pass. The senior file contains 72 visible test
functions. Sol did not execute pytest or RPC.

Jr Dev - Hermes is authorized to integrate exactly the accepted source/test drop plus the aligned
records already present in:

- `docs/adr/0015-data-first-dex-research-substrate.md`
- `docs/handoff/CURRENT_TASK.md`
- `tickets/DEX-003.md`

Before execution, Jr must verify both accepted SHA-256 identities exactly. Jr must run the complete
`tests/acquisition/test_uniswap_v2_pair_events_v2_matrix.py` suite, targeted ruff on the source and
test files, repository control, and diff checks; record exact collection/pass count and duration; then
verify both source/test hashes remain unchanged. If any test or control fails, stop without editing
the accepted source/tests and return evidence to Sol. If all pass, commit and push only these five
DEX-003 files. Do not use destructive reset, clean, or checkout commands.

This source acceptance does not authorize replay, live confirmation, endurance, production
acquisition, coverage credit, publication, factors, PAPER, or LIVE trading. Sol integration acceptance
is required after Jr pushes the commit.

## Sol residual source review - completeness still not closed

The latest drop separates mixed-provider scalar and batch regressions, fixes exact-endpoint versus
same-slug behavior, and deterministically overlaps plan/replay with an active live scanner. It remains
unaccepted. Reviewed identities:

- production source SHA-256
  `9ffafe5664269c0238ff482c63616a11c642dd7288e54ef02348af98daa396e5`
- senior tests SHA-256
  `05f89b2e2cdd4d413d118e18b993e8c234282d254d67584e7a29459098432312`

Two source blockers remain:

1. `_scalar_side` collapses all side outcomes to one failure class. If any scalar is missing but a
   credential, quota, authorization, malformed, transport, or ambiguous blocker also exists, the
   stronger class hides `incomplete`; `evaluate_cells` then emits status `fail`, allowing COMPLETE.
   Completeness and blocker classification must be separate dimensions: any missing required scalar
   keeps cell status `incomplete`, while `failure_class` retains the strongest specific blocker.
2. `_scalar_side` catches every `MatrixSafetyStop` around both `load_body` and `interpret_logs` and
   converts it to ordinary `blocking_failure`. Missing raw objects, digest mismatch, and byte-count
   mismatch are evidence-integrity safety stops and must propagate immediately. Only malformed or
   out-of-domain interpretation of an otherwise authenticated loaded body may be accumulated while
   the remaining scalar evidence is inspected.

The FAILED-terminal regression is not production-path evidence: it monkeypatches `evaluate_cells` to
return fabricated incomplete cells after a fully successful collection. Replace it with a public
`PairEventV2MatrixHarness.run()` test that injects only the execution phase to leave required receipts
absent; unmodified inventory validation and disk `evaluate_cells` must then produce and seal FAILED.
Remove the unused `ChainOnlyTransport` scaffold and commentary. Add missing-plus-stronger-blocker and
raw-integrity propagation regressions.

Sr Dev is authorized for only this residual correction in the same two files. Return explicit scalar
side completeness metadata independently from failure class; combine both providers with
`cell.status=incomplete` whenever either side is incomplete without erasing a stronger blocker class.
Move `load_body` outside the malformed-interpretation catch so raw-integrity failures remain safety
stops. Do not change any other accepted behavior or add scope.

Sr writes but does not execute tests, RPC, records, Git, or commits. Sol must re-review and record new
SHA-256 identities before Jr integration. No destructive Git command is permitted. All live and
downstream prohibitions remain.

## Sol source review - scalar correction rejected

The latest drop adds independent scalar-side evaluation, separate HTTP 403 coverage, deterministic
submission-order fairness, a child-local valid plan for blocked-seal contention, real threaded
plan/replay activity, and removes the unused fake-live run. It remains unaccepted. Reviewed identities:

- production source SHA-256
  `2a0a920284ab79140c27ce814050b8d753131e82b52d3cec31750a31cd8256bc`
- senior tests SHA-256
  `70d74251b8030f8553c5fc2c3dedba30f5f6970bb19a892104ee2021082fc4f7`

Blocking findings:

1. A missing scalar receipt is classified as `incomplete` inside `_scalar_side`, but
   `evaluate_cells` emits every scalar-side problem with cell status `fail`. Harness completeness is
   derived from cell status, so missing mandatory evidence can seal COMPLETE non-PASS instead of
   FAILED.
2. Scalar precedence orders generic `scalar_failure` ahead of `blocking_failure`. A capacity-only
   no-success scalar on one provider can therefore hide authorization, malformed, transport, or
   ambiguous evidence on the other provider. Specific hard blockers must retain their class;
   `scalar_failure` is only the fallback when both side histories contain no stronger blocker.
3. Malformed successful scalar bodies raise immediately during primary-side interpretation, which
   prevents complete inspection of later primary calls and the secondary provider's retained history.
   Disk evaluation must collect both scalar-side outcomes before deciding the cell.
4. The mixed-provider test poisons every scalar, so evaluation exits before the seeded batch evidence
   is inspected. Mixed-provider batch precedence remains untested.
5. The generic-path test still does not allow the same non-secret slug at a different URL, and the
   concurrent scanner-isolation test releases all threads together without proving plan/replay run
   while the live scanner is active.

Sr Dev is authorized for one minimal correction in the same two files. Preserve `incomplete` cell
status whenever any required scalar attempt is absent so the harness seals FAILED. Aggregate both
scalar providers and all scalar logical calls without interpretation short-circuit; retain credential,
quota, authorization, malformed, transport, ambiguous, and incomplete classifications ahead of the
fallback `scalar_failure`. Every scalar side still requires a successful valid body.

Split the mixed-provider regression into scalar and batch cases; the batch case must keep all scalar
references valid, then combine one provider's explicit capacity evidence with the other provider's
hard blocker. Correct the generic-path test by rejecting the exact configured generic endpoint while
allowing the identical non-secret slug on a different host/URL. Make scanner-isolation overlap
deterministic by blocking live transport after its run/scanner is active, executing plan-only and
offline replay during that block, then releasing live. Add a regression proving missing scalar
evidence produces incomplete cells and a FAILED terminal. Do not change any other accepted behavior.

Sr writes but does not execute tests, RPC, records, Git, or commits. Sol must re-review and record new
SHA-256 identities before Jr integration. No destructive Git command is permitted. All live and
downstream prohibitions remain.

## Jr acceptance evidence - corrected drop 74/74 PASS (2026-08-06)

Accepted identities after Sr correction:
- Source SHA-256: 9f84dd007264372ed6499ba3782c0bb34ae0b83090acbf6ed31ff62d715d6a42
- Tests SHA-256: afef397a02ee651542678f19d87f0c01ee55cd21f24d27e67056ca5bbdb6e2f8 (unchanged)

Sequence executed by Jr:
1. Authorization regressions (3/3 PASS, 32.09s): test_http_401_is_hard_blocker,
   test_http_403_is_hard_blocker, test_credential_detection_precedes_http_429_classification.
2. Single failing-test rerun (isolated): test_authorization_detail_with_credential_material_classifies_credential
   PASS (12.48s) against corrected source.
3. Complete suite: 74 collected, 74 passed, 0 failed, exit 0, duration 2341s (~39.0 min).
   Log: logs/dex003/matrix_suite_full_run.log.

Hashes re-verified unchanged after suite. All five DEX-003 files committed; GMGN research draft
(research/sprint_004/52_GMGN_SOLANA_DEX_PROSPECTIVE.md) intentionally excluded, uncommitted.
Live and downstream work remain unauthorized.

## Sol integration acceptance - 90c4082

Sol accepts the corrected capacity-selection integration at pushed commit `90c4082`. The commit
contains exactly the accepted production source, unchanged senior tests, ADR-0015, CURRENT_TASK, and
DEX-003 ticket. The unrelated GMGN prospective research draft remains untracked and is not included.

Committed identities match the accepted drop:

- production source SHA-256
  `9f84dd007264372ed6499ba3782c0bb34ae0b83090acbf6ed31ff62d715d6a42`
- senior tests SHA-256
  `afef397a02ee651542678f19d87f0c01ee55cd21f24d27e67056ca5bbdb6e2f8`

Jr evidence records the three authorization regressions PASS in 32.09 seconds, the prior isolated
failure PASS in 12.48 seconds, and the complete suite at 74 collected / 74 passed / 0 failed / exit 0
in 2,341 seconds. Hashes remained unchanged; targeted ruff, repository control, and diff checks passed.
Sol did not rerun pytest or RPC. `HEAD` and `origin/main` both resolve to `90c4082`.

### Evidence-retention blocker

No live confirmation is authorized yet. The recorded prior evidence root
`data/dex003_v2_matrix/live_0002b70_mtx_29211422` is absent, and none of the three retained run IDs can
be found in the active repository tree:

- `run_32d7c4d9fdc0406f90c768f179663c5a`
- `run_5ed38a9ada6942d5964eeb622963d2d5`
- `run_70e886dd31674d259042d11ac4194763`

Those directories were previously declared immutable retained incident evidence. The owner must
provide their current active location or explicitly report that they were lost. Do not search or use
the historical archive. Do not create a replacement live root, rerun RPC, or treat a future run as a
replacement for missing historical evidence until Sol resolves this retention incident.

The no-network matrix ID still resolves exactly to
`mtx_29211422a0ea5148c1601d39d647e916a57c3227d78026289685a6fb910901c2`; 192,001,794,048 bytes were
free on the data filesystem; RPC endpoint variables were unset in Sol's shell. Replay, live
confirmation, endurance, production acquisition, coverage credit, publication, factors, PAPER, and
LIVE trading remain prohibited.

## Jr live-confirmation evidence - run_f135dda6ab1a48c8967a4b0165547dd7 FAILED (2026-08-07)

Record commit: 89a8491. Source SHA-256 9f84dd007264372ed6499ba3782c0bb34ae0b83090acbf6ed31ff62d715d6a42;
tests SHA-256 afef397a02ee651542678f19d87f0c01ee55cd21f24d27e67056ca5bbdb6e2f8 (unchanged).

- Matrix ID: mtx_29211422a0ea5148c1601d39d647e916a57c3227d78026289685a6fb910901c2 (matches precondition)
- Run ID: run_f135dda6ab1a48c8967a4b0165547dd7
- Terminal kind: FAILED; error_type MatrixSafetyStop; safety_stop "global wall-time budget breached during HTTP"
  context timeout_seconds 60.0; exit code 1; started 16:12:49Z, finished 16:16:53Z, elapsed 244.517s
  (max_wall_seconds 5400 not consumed; per-request 60s budget breached on the blockpi chain call).
- Cells (15/15): all `incomplete` (sparse/medium/hot x cohort 1/8/32/64/128), failure_class incomplete,
  missing_attempts. Detail per cell "primary:incomplete;incomplete;secondary:incomplete;incomplete".
- Capacity selection: selection_valid false, selected_cohort_size null, viable_sizes [], blocking_reasons = all 15
  incomplete cells, capacity_failure_cells [].
- Chain calls: chain:infura SUCCESS (HTTP 200, 39 B, latency 3259.8 ms, body sha256
  1b4c9948350921489f387c8ac3eddf70c737d393b182e71eba1ff4c83a96dc9e); chain:blockpi started but never
  completed (no receipt retained, provider_attempts 2, logical_calls_started 2).
- 429s: 0. Retained response bytes 39, observed 39. In-flight high-water 1 (budget 1).
- Credential scan: pass. evidence_hash 2a9d9eb1a662509bd873908766eadd904185ba5b485b6d01df10639f1626dc58;
  report_hash 188512ff9b3ff665463ae57fa2bc883c1fe5fa4f0b279cb8f6545550bc567812.
- Output bytes: catalog.json 905077, plan.json 8131, raw/1b4c...dc9e.bin 39, receipts/chain__infura__a1.json 779.
- Free disk at seal: 190,280,192,000 bytes (~177 GiB).
- No replay: replay is conditionally authorized only on COMPLETE and PASS; this run is FAILED.
- Output tree preserved untouched; no rerun, no edits, no push of source/tests.

Blocker class: MatrixSafetyStop (transport/timeout on secondary provider chain probe before any cell attempt).
No capacity, replay, endurance, or coverage credit. Next actor: reviewer/Sol - diagnostic decision.

## Sol failed-run review - external isolation violated

Sol accepts `run_f135dda6ab1a48c8967a4b0165547dd7` only as immutable FAILED incident evidence. The harness
behaved correctly: it retained the completed Infura chain response, failed closed when the BlockPI
chain request exceeded its 60-second HTTP budget, drained provider work, sealed FAILED, marked all
cells incomplete, selected no capacity, and did not replay. The run receives no validity or capacity
credit.

Legacy `/home/lars/trading-bot` user services were running or enabled during the attempt, violating the
no-concurrent-work precondition. Their causal role in the BlockPI timeout is not provable; they use
other exchange/GeckoTerminal workloads and may only have contributed workstation or network pressure.
The failure is transport timeout evidence, not provider capacity evidence.

The owner stopped and disabled the legacy services. Sol independently verified all four units are now
`inactive` and `disabled`, with no matching acquisition/backfill process running:

- `trading-bot-data.service`
- `trading-bot-dex-sampler.service`
- `trading-bot-dex-backfill.service`
- `collector-daemon.service`

The failed root `data/dex003_v2_matrix/live_90c4082_mtx_29211422` must remain untouched. Its lock file,
run directory, FAILED terminal, raw object, and receipts may not be deleted, edited, resumed, or reused.

## Authorized clean replacement - one run only

Because the authorized run began under a violated isolation precondition and failed before any matrix
cell call, Sol authorizes exactly one separately named clean replacement run. This is a new run, not a
resume or automatic retry. One standalone replay remains conditional on replacement COMPLETE and PASS.

### Replacement preconditions

1. Jr first commits and pushes only this Sol review in `docs/handoff/CURRENT_TASK.md` and
   `tickets/DEX-003.md`; exclude the untracked GMGN draft. Source/test hashes remain the accepted
   `9f84dd007264372ed6499ba3782c0bb34ae0b83090acbf6ed31ff62d715d6a42` and
   `afef397a02ee651542678f19d87f0c01ee55cd21f24d27e67056ca5bbdb6e2f8`.
2. Immediately before execution, all four named legacy services must report both `inactive` and
   `disabled`, and no legacy acquisition/backfill process may be running. Preserve the command output
   without endpoint values.
3. The no-network matrix-ID command must print exactly
   `mtx_29211422a0ea5148c1601d39d647e916a57c3227d78026289685a6fb910901c2`.
4. The owner supplies distinct Infura and BlockPI URLs through the two runtime environment variables;
   never display or persist their values.
5. Both new roots must be absent and non-symlinked:
   `data/dex003_v2_matrix/live_951e127_clean_mtx_29211422` and
   `data/dex003_v2_matrix/replay_951e127_clean_mtx_29211422`.
6. At least 8 GiB free disk and no tests, daemons, backfills, acquisition, or other high-load work.
   Foreground execution only; no detachment or automatic restart.

The replacement uses the prior authorized command unchanged except for its fresh output root:

```bash
uv run python scripts/research/run_uniswap_v2_pair_events_v2_matrix.py \
  --registry-store-root data/dex003_full/store \
  --output-root data/dex003_v2_matrix/live_951e127_clean_mtx_29211422 \
  --execute-live \
  --confirm-matrix-id mtx_29211422a0ea5148c1601d39d647e916a57c3227d78026289685a6fb910901c2 \
  --max-logical-calls 1568 \
  --max-attempts-per-call 3 \
  --max-provider-attempts 4704 \
  --max-wall-seconds 5400 \
  --max-retained-response-bytes 2147483648 \
  --max-response-bytes 8388608 \
  --requests-per-second 0.5 \
  --max-in-flight 1 \
  --http-timeout-seconds 60
```

If and only if replacement live is COMPLETE and PASS, run one standalone replay to
`data/dex003_v2_matrix/replay_951e127_clean_mtx_29211422` using its credential-free `run_dir`.

All prior immediate stops and evidence requirements remain in force. Any replacement failure ends the
phase with no third run. Preserve both the original failed tree and the replacement tree. No result
authorizes endurance, production acquisition, publication, factors, PAPER, or LIVE trading.

## Replacement authorization suspended - orphan process discovered

After the replacement decision, the owner disclosed a second isolation violation present during the
failed live window: orphan process PID 2687 ran `/home/lars/trading-bot/dex_ohlcv_sampler.py` from July
25 even though `trading-bot-dex-sampler.service` later reported inactive/disabled. The orphan is now
absent, proving service-unit state alone is not a sufficient process-isolation check.

Sol also observes Grok PID `2309342`, started 2026-08-02T20:39:20 local time, still running at about
87% CPU. That is a prohibited high-load concurrent process. Grok PID `2470211` is present at low CPU,
but any agent work must be idle during the live window.

The clean replacement authorization above is suspended and must not be executed or published as
executable authorization yet. The owner must stop or otherwise terminate the high-CPU Grok process and
confirm no legacy sampler/poller/backfill/collector process remains. Sol must then verify:

- no `dex_ohlcv_sampler.py`, `data_poller.py`, `backfill_dex_history_gt.py`, or
  `collector_daemon.py` process;
- all four named legacy units inactive and disabled;
- no Grok or other agent process consuming sustained high CPU;
- no matrix/test/acquisition process and no new replacement output root.

Only after a fresh process-level check passes may Sol reactivate the single clean replacement. No RPC,
record publication, replacement root creation, replay, or other DEX-003 execution is authorized while
this suspension is active.

## Sol process-level clearance - replacement reactivated

Sol rechecked the host after the owner stopped the remaining processes. Both Grok PIDs `2309342` and
`2470211` are absent. No `dex_ohlcv_sampler.py`, `data_poller.py`,
`backfill_dex_history_gt.py`, `collector_daemon.py`, matrix runner, or matrix pytest process is running.
All four named legacy units remain inactive and disabled. The two replacement roots remain absent and
nonexistent. Free data-filesystem space is 189,923,172,352 bytes.

The single clean replacement authorization above is reactivated. Jr must first commit and push only
the accumulated Sol review/suspension/clearance records in CURRENT_TASK and DEX-003, excluding the
untracked GMGN draft. Immediately before RPC execution, Jr must repeat and preserve the process-level
and service checks. Any matching process, active/enabled legacy unit, sustained high-CPU agent job,
new output root, or concurrent high-load task reinstates the stop automatically.

If the immediate preflight remains clean, Jr may execute exactly the one foreground replacement
command already frozen above, followed by one standalone replay only on COMPLETE and PASS. Any
replacement failure ends the phase; no third run is authorized.

## Environmental context - FAILED live run possibly confounded (2026-08-07)

Post-run inspection by owner/Jr:
- Concurrent background processes running the entire time (not just collector_daemon PID 2680):
  `/home/lars/trading-bot/dex_ohlcv_sampler.py` PID 2687 (up since Jul 25) — a DEX-related OHLCV
  sampler; plus `grok` PID 2309342 at ~87% CPU, xeoma, browsers. Precondition 6 (no concurrent
  daemon/acquisition/high-load jobs) was therefore NOT satisfied during the live window.
- VPN: WireGuard tunnel `azirevpn-za-jnb` (AzireVPN, Johannesburg/ZA, mtu 1420) is UP since Aug 4
  with policy rule `not from all fwmark 0xca6c lookup 51820`. RPC endpoints are NOT tagged to bypass:
  - mainnet.infura.io -> 63.186.95.78 routes via table 51820 (tunnel)
  - ethereum.public.blockpi.network -> 2606:4700:3034::6815:2838 (IPv6) routes via tunnel
- Interpretation: the BlockPI probe hang (MatrixSafetyStop, per-request 60s budget) may be caused by
  the South Africa tunnel path (IPv6 egress) and/or concurrent DEX sampler load, not by a harness
  defect. Infura (IPv4 via tunnel) succeeded in 3.26s.
- No rerun is authorized or executed; this context does not alter the FAILED verdict of
  run_f135dda6ab1a48c8967a4b0165547dd7. Evidence tree preserved. Reviewer decides next step
  (e.g., bypass-tag RPC hosts, re-check preconditions, then one fresh live run).

## Network change - RPC/DEX provider fwmark bypass installed (2026-08-07)

Owner installed nftables table `inet dex_bypass` (chain output, priority mangle) tagging egress to
non-geoblocking data providers with fwmark 0xca6c, which policy rule `not from all fwmark 0xca6c
lookup 51820` routes via the main table (enp6s0) instead of the AzireVPN South-Africa WireGuard
tunnel. Providers bypassed (14 rules, verified in `nft list table inet dex_bypass`):
- RPC: Infura (mainnet.infura.io v4 x3), Alchemy (eth-mainnet.g.alchemy.com v4 x3),
  BlockPI (ethereum.public.blockpi.network v4+v6) - the provider whose probe hung in the FAILED run.
- DEX/aggregator: DexScreener (v4+v6), GeckoTerminal (v4+v6), Birdeye (v4+v6), CoinGecko (v4+v6),
  DefiLlama coins.llama.fi + yields.llama.fi (v4+v6).
- CEXes with geoblocking (Binance api.binance.com, Bitmex www.bitmex.com) intentionally remain on
  the tunnel and are NOT tagged.

Verification: `ip route get <provider-ip> mark 0xca6c` -> via 192.168.1.1 dev enp6s0 (direct);
live probes via IPv4: BlockPI reachable, DexScreener 200, CoinGecko 200, Birdeye 401 (auth, reachable).
Caveat: IPv6 for tagged providers is now unreachable via the main table (no direct IPv6 default);
dual-stack clients fall back to IPv4 (verified with curl -4). Marks are IP-based, so DNS rotations
would require re-adding new addresses. Rules are in-memory only; persistence (nftables.conf) is the
owner's decision. No matrix rerun was executed; FAILED verdict for run_f135dda6ab1a48c8967a4b0165547dd7
stands. Reviewer may now consider authorizing one fresh live confirmation.

## Jr clean replacement evidence - live COMPLETE+PASS, replay COMPLETE+PASS (2026-08-07)

Record commit 483a5e2. Source SHA-256 9f84dd007264372ed6499ba3782c0bb34ae0b83090acbf6ed31ff62d715d6a42;
tests SHA-256 afef397a02ee651542678f19d87f0c01ee55cd21f24d27e67056ca5bbdb6e2f8 (unchanged after runs).

### Preflight (immediately before execution)
- No grok/dex_ohlcv_sampler/data_poller/backfill_dex_history_gt/collector_daemon process.
- No matrix or matrix pytest process. All four legacy services inactive AND disabled.
- Matrix ID matches exactly. Replacement roots absent and non-symlinked.
- Free disk 189,833,768,960 bytes; only GUI processes at load (no high-CPU agent).
- RPC URLs loaded from owner .env; values never displayed or persisted.

### Live replacement - run_f2fd323fcd69403a923f6329b9f0c320
- Terminal COMPLETE, pass true, exit 0; started 16:54:42Z, finished 17:24:45Z, elapsed 1803.696s.
- Logical calls started 1568, provider attempts 1580, HTTP 429s 0, high-water in-flight 1.
- Retained bytes 144,991,333; observed body bytes 177,521,737; 1580 receipts, 298 raw files.
- Cells (15): 12 PASS with provider agreement; 3 capacity FAIL (medium:cohort32/64/128).
  For each failed cell, both scalar references succeeded with equal identity-v2 digests, while
  both batches failed authenticated capacity limits, so batch/scalar equality was not evaluable.
  All sparse and hot cells PASS.
- Capacity selection: valid, selected_cohort_size 8, viable_sizes [1,8],
  capacity_failure_cells medium:cohort32/64/128, nonmonotonic false.
- credential_scan pass; evidence_hash e42e987dade698af6af4fb47598abe88eb78116ac6fc004ff6fc4d0a84b4a114;
  report_hash 2062d1f8717672de645f07bd761354bea31cdca9dbe20908cfe3941fb00189ef.
- Both chain probes succeeded (infura, blockpi) - BlockPI bypass confirmed.
- Recommendation: capacity_selection_valid true, suggested_cohort_size 8, authorizes_endurance false,
  grants_v2_coverage false, frozen false.

### Standalone replay - run_bd066d2e228d46728a97fdb61138e365
- Terminal COMPLETE, pass true, exit 0; 31.359s; offline (0 logical calls, 0 provider attempts).
- All 15 cells identical to live (12 PASS, 3 capacity FAIL); capacity selection identical (cohort 8).
- credential_scan pass; evidence_hash f7b536de7823a298688e935efae82f85971957c440c7ccdea96881b0b72b88a2;
  report_hash 6c27a8df5211991487d2d0d61dbac548a94f2f4c41a17393ee2846a5ec165786.
- Output roots: data/dex003_v2_matrix/live_951e127_clean_mtx_29211422 and
  data/dex003_v2_matrix/replay_951e127_clean_mtx_29211422. Both trees preserved.
- Free disk after runs 556,977,242,112 bytes.

No result authorizes endurance, production acquisition, publication, factors, PAPER, or LIVE trading.
Next actor: reviewer/Sol - capacity-selection and evidence review of the clean replacement.

## Sol acceptance - authenticated matrix capacity 8 (2026-08-07)

Sol accepts the clean replacement and its standalone replay at pushed record commit `38b8d70`.
Sol independently ran the read-only `authenticate_completed_run` path against both preserved trees;
Sol did not rerun pytest and made no RPC call. `HEAD` and `origin/main` both resolved to `38b8d70`
before this review, and the production/test identities remain:

- production source SHA-256
  `9f84dd007264372ed6499ba3782c0bb34ae0b83090acbf6ed31ff62d715d6a42`
- senior tests SHA-256
  `afef397a02ee651542678f19d87f0c01ee55cd21f24d27e67056ca5bbdb6e2f8`

The authenticated live run `run_f2fd323fcd69403a923f6329b9f0c320` is COMPLETE/PASS with 1,568
logical calls, 1,580 provider attempts, zero HTTP 429s, 144,991,333 retained bytes, credential scan
PASS, evidence hash `e42e987dade698af6af4fb47598abe88eb78116ac6fc004ff6fc4d0a84b4a114`, and report
hash `2062d1f8717672de645f07bd761354bea31cdca9dbe20908cfe3941fb00189ef`. Twelve cells are
universally viable. In `medium:cohort32`, `medium:cohort64`, and `medium:cohort128`, both providers'
mandatory scalar references succeeded and produced equal identity-v2 digests; Infura batches failed
`provider_limit_or_size` and BlockPI batches failed `body_size_pressure`. These are authenticated
capacity boundaries under ADR-0015 section 9.8, not quota, credential, malformed-evidence, digest,
provider-disagreement, or nonmonotonic blockers.

The read-only standalone replay `run_bd066d2e228d46728a97fdb61138e365` is COMPLETE/PASS with zero
logical calls and zero provider attempts. It reproduces all 15 cell decisions and the valid capacity
selection exactly, with evidence hash `f7b536de7823a298688e935efae82f85971957c440c7ccdea96881b0b72b88a2`
and report hash `6c27a8df5211991487d2d0d61dbac548a94f2f4c41a17393ee2846a5ec165786`.

Sol therefore accepts cohort size `8` as the authenticated initial-cohort input to the next bounded
endurance-design phase. This does not grant v2 coverage, accept an endurance result, authorize an
endurance execution, freeze production execution settings other than the initial cohort, or authorize
full acquisition. The three lost historical runs and FAILED
`run_f135dda6ab1a48c8967a4b0165547dd7` remain incident evidence only and receive no capacity or
coverage credit. Preserve all current live, replay, and FAILED evidence trees unchanged.

## Authorized next phase - endurance-harness design only

Jr Dev - Hermes must first commit and push only this Sol acceptance/design authorization in
`docs/handoff/CURRENT_TASK.md` and `tickets/DEX-003.md`, excluding the unrelated untracked GMGN
draft. After that publication, Sol authorizes Sr Dev - Grok Build to produce exactly one uncommitted
design proposal at `research/sprint_004/53_DEX003_V2_ENDURANCE_HARNESS_DESIGN.md`. The senior phase
is reasoning and design only: no production source, test source, migrations, ADR, repository records,
data, commands, RPC, pytest, Git, commit, or push work is authorized.

The proposal must specify the smallest fail-closed 6-24 hour endurance harness around the accepted
`PairEventV2Engine` and answer each of these points concretely:

1. Authenticate the exact accepted matrix plan, live tree, replay tree, run IDs, terminal manifests,
   evidence/report hashes, valid selected cohort `8`, accepted registry manifest, dataset ID, parquet
   path, byte count, and SHA-256 before creating endurance state. No caller-supplied pools, cohort,
   ranges, topics, providers, or production plan identity may override those authorities.
2. Define a dedicated endurance identity, root, receipt database, raw store, spool, immutable
   checkpoints, and terminal report. Refuse `dex003_full.db`, accepted registry/catalog paths, matrix
   evidence trees, production v2 state, path overlap, and symlinks. The pilot grants no production
   coverage and may not present a partial or sampled node set under the full production plan identity.
3. Define a deterministic workload schedule that is representative across the pre-2025 block span,
   pool-birth growth, sparse/medium/hot event density, adaptive address/block splits, retries, and
   shared-header demand. Explain how that schedule uses only public authenticated engine/foundation
   APIs. If the accepted APIs cannot support it without misrepresenting plan identity or directly
   mutating private SQLite state, identify the minimum API/schema/ADR change instead of bypassing the
   boundary.
4. Define the exact throughput numerator and clock denominator. The numerator must be durably AGREED,
   non-overlapping, birth-clamped pool/topic/block coverage converted to 5,000-block scalar-equivalent
   units, not claims, requests, raw receipts, attempted nodes, or optimistic parent domains. PASS must
   require at least `36,220` such units/hour, exactly 20 times the recorded scalar baseline of 1,811.
5. Define end-to-end projections for complete event logs plus shared headers using observed net
   authoritative throughput, split/retry amplification, header fan-out/cache behavior, evidence bytes,
   and initialization/finalization cost. PASS requires a target projection of at most seven days, a
   hard maximum of fourteen days, and projected retained evidence that leaves at least 2x free-disk
   headroom; state exact formulas and conservative treatment of unobserved strata.
6. Define bounded memory, provider requests/in-flight work, node/persistence queues, spool files,
   retries, response bytes, writer latency, SQLite latency/size, checkpoint cadence, credential scans,
   and process/resource high-water metrics. Define immediate safety stops and terminal FAILED versus
   completed-non-PASS semantics.
7. Define monotonic 6-hour minimum and 24-hour hard-stop behavior, including stop-new-work, drain,
   durable checkpoint, clean engine/thread/client closure, crash recovery, resume accounting, and
   prevention of elapsed-time or evidence-counter reset across process restarts.
8. List the proposed production/test file scope, public CLI contract, fake-clock/fake-transport
   offline tests, decisive tamper/crash/resource/projection regressions, and any strictly necessary
   accepted-engine or foundation change. Prefer new isolated files; justify every edit to accepted
   source. Sr stops after delivering this design for Sol review.

No endurance harness implementation or execution is authorized by this design phase. Production
acquisition, publication, coverage credit, metadata/downstream transforms, factor work, PAPER, and
LIVE trading remain prohibited. Next ticket authorized remains `NONE`.

## Sol review - endurance-harness design rejected (2026-08-07)

Jr published the matrix acceptance/design authorization at commit `ac5a282`; `HEAD` and
`origin/main` both resolve to that commit. Sr then delivered the sole authorized uncommitted proposal
`research/sprint_004/53_DEX003_V2_ENDURANCE_HARNESS_DESIGN.md`, SHA-256
`f6c343b3ccb02fe1cea783c924bffa1db58683ec336e8e6bbf58e81c0e0d87e6`. No production/test
source, migrations, ADR, data, RPC, pytest, Git, commit, or push work accompanied the proposal.

The proposal correctly identifies that the accepted engine cannot install a representative partial
pilot under the full production plan identity and that direct private-SQLite scheduling would be a
second scheduler. It also correctly distinguishes AGREED birth-clamped coverage from requests and
shows that the 20x floor alone cannot meet the fourteen-day projection. The design is nevertheless
rejected before implementation for these blocking defects:

1. The proposed `eplan_<hash>` identity cannot enter the accepted foundation or database. Every
   `_require_plan_id`/record validator requires `plan_<64 hex>`; `PlanRecord` reconstructs a production
   `PlanConfig`; and migrations 0017-0019 constrain/foreign-key the same production plan rows. The
   proposal authorizes no migration and does not define the discriminated pilot-plan record, schema,
   authentication, or fresh-database bootstrap needed by its own API changes. Applying only migrations
   0017-0019 to a fresh DB is also invalid because 0018 references earlier raw-object tables.
2. The schedule cannot produce a PASS. Its ceiling of 25,000 roots contains at most 400,000 SEU
   (`25,000 * 8 pools * 2 topics`) before birth clamping. Even if every root agrees, six hours caps the
   rate at 66,666.67 SEU/hour, below the 176,793.71 SEU/hour required to project 29,701,343.35 SEU to
   seven days. At the proposed default continuation to 24 hours it caps at 16,666.67 SEU/hour, below
   even the 36,220 floor. The under-2,000 expansion rule is not an exact selection algorithm. In
   addition, `S_late` selects windows near block 25,600,000 rather than remaining inside the authorized
   pre-2025 pilot span.
3. `R_net` already measures net AGREED SEU per elapsed hour after observed splits, retries, headers,
   and persistence. Multiplying `U_full / R_net` by absolute observed split/retry amplification counts
   those costs twice. The fixed `w_hot=0.35` penalty is unsupported. Projection must use explicit
   full-lattice stratum weights and conservative observed stratum rates without fitted or arbitrary
   constants.
4. PASS semantics are contradictory. Section 5 requires seven days, but the terminal table allows
   PASS whenever only the fourteen-day hard maximum is met. The frozen contract requires projection
   at or below seven days for PASS. A result above seven and at/below fourteen days is COMPLETE
   non-PASS; above fourteen days is COMPLETE non-PASS plus mandatory stop-for-redesign unless another
   safety defect independently requires FAILED.
5. Wall-clock subtraction alone does not satisfy the monotonic-duration gate, and downtime cannot
   count toward six hours of endurance observation. The proposal explicitly permits PASS after an
   interrupted wall span without six active monotonic hours. It also lacks fail-closed wall-clock
   rollback/jump handling across checkpoints and resumes.
6. The accepted engine rejects sensitive JSON keys but does not scan every streamed response byte for
   exact runtime endpoints/secrets or credential forms before raw persistence. The proposal incorrectly
   assumes engine-scanned raw bodies and proposes only a later partial metadata scan. Credential-bearing
   bytes must never be persisted; the design must include the minimum engine streaming-scanner surface
   and boundary/over-cap/error-body tests.
7. The proposal has no complete immutable evidence inventory or public read-only terminal
   authenticator. Hashing a report/checkpoint is insufficient while `receipt.db`, raw objects,
   checkpoints, logs, and run files remain mutable or unauthenticated. It must define clean-close,
   exact file inventory/hash sealing, extra/missing/path-escape rejection, authenticated DB/row/raw
   relationships, offline recomputation of SEU and projections, and source-tree immutability during
   review.
8. Several required resource metrics are not exposed by `EngineMetrics`, including provider attempt
   totals and provider in-flight high-water. The minimum additive engine surface and tests must be
   listed rather than assigning unavailable values to the harness. Disk headroom must use free space
   at the terminal decision (and exact total projected storage categories), not only pre-run free space.

## Authorized correction - same design file only

Jr Dev - Hermes must first commit and push only this review in `docs/handoff/CURRENT_TASK.md` and
`tickets/DEX-003.md`, excluding both untracked research files. After publication, Sr Dev - Grok Build
may revise only `research/sprint_004/53_DEX003_V2_ENDURANCE_HARNESS_DESIGN.md`. No source, tests,
migration, ADR, other record, data, command, RPC, pytest, Git, commit, or push work is authorized.

The corrected proposal must:

1. Choose one exact pilot-plan persistence design that is valid through foundation validators,
   authenticated record reconstruction, SQLite checks/FKs, and the migration runner. Specify every
   additive production/test/migration/ADR file that a later implementation would require and the exact
   fresh dedicated-DB bootstrap. Do not use `eplan_` with current validators, reuse the production plan
   identity for a subset, weaken production authentication, or bypass the coordinator with private SQL.
2. Replace the root-count target with deterministic scheduled-SEU sizing. For an intended active
   duration `D` in 6-24 hours, the schedule must contain enough birth-clamped SEU to sustain at least
   `U_full / 168 * D`, plus a declared conservative reserve for partial cohorts and unusable/failed
   strata. Define the expansion algorithm byte-exactly, prevent premature idle/exhaustion, and use only
   authenticated windows ending in the authorized pre-2025 span. The selected duration and schedule
   digest are immutable identity inputs.
3. Define projection from net observed per-stratum AGREED rates and exact full-lattice SEU weights.
   Observed split/retry/header/persistence costs remain reported diagnostics but are not multiplied into
   the same net rate again. Define conservative handling for sparse or unobserved strata without an
   unsupported fitted constant. Require `<=7 days` for PASS, classify `>7 and <=14` as COMPLETE
   non-PASS, and classify `>14` as COMPLETE non-PASS with mandatory redesign stop.
4. Require at least six accumulated active monotonic hours for PASS; downtime never satisfies that
   minimum. Preserve first wall start, monotonic process segments, downtime, and resume count; include
   downtime in the throughput denominator; reject wall-clock regression/inconsistent jumps; stop new
   work by the immutable 24-hour wall deadline and an in-process monotonic backstop. State exact early
   stop and schedule-exhaustion semantics.
5. Add pre-persistence rolling scanning of every streamed response byte, including chunk boundaries,
   provider error bodies, truncation/over-cap drains, exact runtime URLs and extracted secrets, and
   generic credential forms. A hit drains safely, persists no secret bytes, and seals FAILED with only
   a canonical redacted marker.
6. Define an immutable terminal evidence protocol and public zero-network authenticator: clean engine
   closure, exact inventory and SHA-256 for the plan, dedicated DB snapshot, raw objects, checkpoints,
   metrics, and terminal artifacts; no extras; path/symlink rejection; relational/raw authentication;
   recomputed schedule/SEU/projection/outcome; and read-only review that cannot mutate the source tree.
7. Enumerate all new engine metrics/APIs required for provider attempts, actual in-flight high-water,
   spool/queue bounds, authenticated leaf/header iteration, pilot initialization/resume, and clean
   drain. Define terminal disk projection from exact observed total tree/DB/checkpoint bytes per SEU and
   conservative stratum statistics, tested against current terminal free space with 2x headroom.
8. Resolve the run/root/checkpoint model so crashes leave an authenticatable incomplete run, one resume
   cannot reset identity/time/counters, and exactly one immutable terminal exists for the endurance
   identity. Expand the decisive offline test list to cover every correction above.

Sr stops after replacing the design proposal for Sol re-review. Endurance implementation/execution,
production acquisition, publication, coverage credit, metadata/downstream transforms, factor work,
PAPER, and LIVE trading remain prohibited. Next ticket authorized remains `NONE`.

## Sol re-review - corrected endurance design rejected (2026-08-07)

Jr published the first design rejection/correction authorization at commit `5b4af4a`; `HEAD` and
`origin/main` both resolve to that commit. Sr revised only the authorized untracked proposal. The
corrected `research/sprint_004/53_DEX003_V2_ENDURANCE_HARNESS_DESIGN.md` has SHA-256
`51f36d9e1f9c9f36bd0ea868d9d4f4f25b8ebaba79bc1b31130b8d85e29924c7`; the unrelated GMGN
draft remains untracked, and no source/test/migration/ADR/record/data/Git change accompanies the design.

The correction closes the invalid `eplan_` prefix, standalone-0017 bootstrap, 25,000-root capacity,
seven-versus-fourteen-day terminal class, downtime-as-active-time, missing scanner, missing public
authenticator, and missing-metrics acknowledgements. It is still rejected before implementation for
the following blockers:

1. Construction order is not execution order. The proposed schedule round-robins strata while
   selecting roots, but accepted `_op_claim_pending` executes `ORDER BY start_block, domain_id`.
   Consequently early roots can consume the observation window before hot/late/post-pin strata run;
   mandatory roots in the DB do not prove representative work. The design neither persists an
   identity-bound root priority nor defines deterministic priority inheritance for split children.
2. The stratum projection is mathematically invalid. `SEU_s / total_wall_elapsed` is each stratum's
   contribution to global throughput, not that stratum's processing rate. Weighting those contributions
   by `w_s` applies sample shares again. Even with valid stratum rates, completion time is additive:
   `T_work = sum_s(U_s / R_s_use)` (the weighted-harmonic equivalent), not
   `U_full / sum_s(w_s * R_s_use)`. If total wall already includes initialization/finalization, adding
   `T_init + T_final` again also double-counts them.
3. Treating every unobserved post-pin stratum as the slowest observed pre-pin rate is not a conservative
   bound on denser later data. A full-cutoff PASS cannot rely on that assumption. DEX-003's holdout rule
   permits structural acquisition/quality metrics but no factor, return, ranking, or portfolio output;
   the next design may include deterministic structural-only strata through the pinned cutoff so every
   projection stratum is actually observed.
4. The plan/schema choice remains non-exact. It alternates between adding pilot fields to `PlanConfig`
   and an `AcquisitionPlanV2`-shaped object, while migration 0020 enforcement is left as “triggers or
   documented app-level” behavior. Changing the parent plan-table CHECK requires an exact forward
   migration that preserves existing populated v1 rows and all child FKs. The proposed migration test
   covers only an empty DB and omits populated upgrade, v1 identity preservation, invalid-v2 rejection,
   and atomic rollback.
5. Identity arithmetic is still float-based: millions of fractional SEUs are summed as IEEE float and
   rounded to twelve decimals. SEU has an exact integer numerator in pool-topic-blocks over denominator
   5,000; schedule identity and all gates must use that rational/integer authority, never float rounding.
6. `wall_segments.jsonl` is declared append-only but its start record is later “filled” with end fields.
   A crashed process cannot recover an unpersisted `mono_end`. The design must use immutable start/end/
   checkpoint events and state exactly how much active monotonic time an unmatched crash segment earns.
7. The credential path says scanning precedes promotion, not every spool write. A secret spanning chunks
   can place its prefix in a disk spool before the next chunk completes the match. The scanner needs a
   bounded holdback window at least as long as its longest exact needle and must release only bytes proven
   safe; tests must assert no secret bytes in spool, raw, DB, logs, checkpoints, or terminals.
8. Terminal hashing remains ambiguous/self-referential. `TERMINAL.json` claims every allowed file but
   cannot inventory/hash itself; optional sidecars and empty directories are not canonicalized; and the
   design permits authority-bearing wall timestamps/elapsed fields to remain unhashed even though they
   determine throughput and PASS. The pre-terminal manifest, terminal hash construction, exact allowed
   inventory, immutable authority fields, SQLite sidecars, and post-seal no-write rule must be explicit.
   Disk projection's 75th-percentile interval rate is also not conservative for a hard 2x gate.

## Authorized second correction - design file only

Jr Dev - Hermes must first commit and push only this re-review in `docs/handoff/CURRENT_TASK.md` and
`tickets/DEX-003.md`, excluding both untracked research files. After publication, Sr Dev - Grok Build
may revise only `research/sprint_004/53_DEX003_V2_ENDURANCE_HARNESS_DESIGN.md`. No source, tests,
migration, ADR, other record, data, RPC, pytest, Git, commit, or push work is authorized.

The next revision must:

1. Define an identity-bound execution schedule, not merely a selected root set. Specify the minimum
   persisted `schedule_rank`/stratum fields, exact coordinator claim order, resume authentication, and
   deterministic placement/priority of adaptive children. Prove each required stratum receives a
   minimum scheduled and executed SEU allocation before PASS eligibility; schedule exhaustion or a
   missing stratum is COMPLETE non-PASS.
2. Measure stratum rates in non-overlapping, identity-bound execution epochs (or another exact method
   that assigns both SEU and elapsed cost once under concurrency). Project
   `T_work = sum_s(U_s / R_s_use)` and add fixed costs only if excluded from rate denominators. Report
   the equivalent harmonic net rate. Splits/retries/headers remain inside measured net epoch rates and
   are not multiplied again.
3. Remove the unauthenticated post-pin substitution. The structural endurance schedule may sample
   deterministic windows through block 25,600,000, including holdout/post-holdout periods, solely for
   request/byte/log-count/split/header/latency/resource metrics. It must not decode, report, rank, or
   expose prices, returns, factors, pools, or portfolio outcomes. Every full-lattice projection stratum
   must have a minimum observed allocation; otherwise PASS is impossible.
4. Choose explicit `EndurancePilotPlanConfig`/record types and a complete schema-v2 payload rather than
   optional pilot fields on production `PlanConfig`. Specify migration 0020's exact table/trigger/index/
   FK operations and fresh bootstrap. Require tests for a populated 0019-to-0020 upgrade with all v1
   rows/child relationships preserved, byte-identical v1 identities, valid v2 insertion, malformed or
   coverage-granting v2 rejection, FK checks, and atomic rollback. No “app-level or trigger” alternative
   may remain.
5. Represent scheduled and completed coverage as exact integer `pool_topic_blocks`; derive SEU only as
   the rational `pool_topic_blocks / 5000` for display. Identity, thresholds, schedule exhaustion,
   projections, and authentication use integers/rationals or fixed cross-multlication.
6. Replace mutable segment rows with append-only START, CHECKPOINT, END, CRASH/RESUME events. Credit a
   crashed segment only through its last durable monotonic checkpoint; bind boot/process identity,
   reject unmatched/reordered events, and hash every wall/monotonic duration that affects eligibility,
   deadline, throughput, projection, or outcome.
7. Define the stream scanner's pre-write holdback algorithm and maximum-needle bound. No candidate byte
   may reach spool/raw persistence until it can no longer participate in a secret match. Continue scanning
   all drained over-cap/error bytes; on detection delete any safe-prefix spool, persist no response body,
   and retain only the canonical redacted failure record.
8. Use a separate canonical `MANIFEST.json` that hashes every pre-seal regular file and excludes only
   itself, the final terminal, the held lock file, and canonical empty transient directories by explicit
   rule. `TERMINAL.json` hashes the manifest and every decision/clock/projection field with hash fields
   omitted during canonicalization; it is then exclusive-created and no source-root writes are allowed.
   The authenticator rejects WAL/SHM or any unlisted object and opens the DB immutable read-only. Disk
   projection uses exact total observed bytes and the maximum authenticated per-stratum bytes-per-
   pool-topic-block rate plus declared fixed overhead, tested against terminal free space at 2x.

Sr stops after replacing the same design for Sol re-review. Harness implementation, migration/ADR/source
work, test execution, RPC, endurance execution, production acquisition, publication, coverage credit,
metadata/downstream transforms, factor work, PAPER, and LIVE trading remain prohibited. Next ticket
authorized remains `NONE`.

## Sol re-review - second endurance-design correction rejected (2026-08-08)

Jr published the preceding rejection and correction authorization at commit `afac3b4`; `HEAD` and
`origin/main` both resolve to that commit. Sr revised only the authorized untracked proposal. The current
`research/sprint_004/53_DEX003_V2_ENDURANCE_HARNESS_DESIGN.md` has SHA-256
`e7787881247e30507b351dc53810f46da57c2659f9d9eac0f495697963d098e3`. The unrelated modified
`opencode.json` and untracked GMGN research draft remain outside DEX-003 review scope. No implementation,
migration, ADR, test execution, RPC, data, or Git action accompanied the design.

The proposal correctly moves schedule and gate authority to integer pool-topic-blocks, samples structural
windows through the cutoff, adds persisted schedule ranks, uses an additive stratum projection, separates
the pilot config, defines append-only clock events and pre-write scanner holdback, and separates manifest
from terminal hashing. It remains rejected before implementation for the following blocking defects:

1. COMPLETE PASS is mathematically unreachable under the declared resource ceilings. The accepted
   registry independently reconciles to `U_full_ptb = 148,506,716,734`. A full cohort-8 root contributes
   at most 80,000 PTB. At two requests/second per provider and two nodes in flight, the ideal no-overhead
   ceiling is 576,000,000 PTB/hour, implying 10.74 days for the full lattice. The required seven-day rate
   is about 883,968,552 PTB/hour. Retries, splits, headers, partial cohorts, latency, and persistence only
   reduce the observed rate. The default 12-hour schedule floor also requires at least 172,374 perfect
   roots and 23.94 hours at that ideal ceiling, leaving no credible execution margin before the 24-hour
   wall deadline.
2. The identity schedule is not byte-exact. `birth_growth` does not define its quantile convention or
   tie/window mapping; `header_band` does not identify its four windows or eight cohort bands; the deploy
   stratum has only two roots under the literal first-three-window rule, so picks `(0, -1, mid)` can select
   one root twice; and the builder may "optionally continue" after its gates. No exact entry count,
   per-stratum PTB totals, or resulting digest is supplied. Each choice changes plan identity.
3. Rank inheritance does not enforce the stated child-before-later-root execution order. With two nodes
   in flight, rank `r+1` may already be claimed before rank `r` splits. Assigning children rank `r` only
   orders still-PENDING rows; it cannot recall later work already in flight. A rank barrier or an exact
   equivalent is required if descendant completion is part of schedule-order authority.
4. Migration 0020 is not valid under the accepted migration runner. The runner enables foreign keys and
   begins `BEGIN IMMEDIATE` before executing migration statements, so the proposed in-transaction
   `PRAGMA foreign_keys = OFF` is ineffective. Dropping/replacing the populated plan parent while its
   0017-0019 children remain attached can fail or cascade data. The query-node rebuild is only described
   conceptually and omits complete DDL, copy/drop order, dependent-table handling, triggers, and index/FK
   recreation. The populated-upgrade test also omits coverage, chain-identity, execution-policy, and
   terminal-receipt rows. This is not the exact populated forward migration previously required.
5. The concurrency cost ledger does not assign all elapsed work exactly once. It discards intervals with
   zero nodes marked IN_FLIGHT even though claim, coordinator, commit, queue, and persistence gaps can
   occur there; those intervals are not assigned to initialization or finalization either. Converting
   each interval to integer milliseconds before allocation can repeatedly discard sub-millisecond time.
   `P_s > 0, C_s_ms = 0` also has no explicit non-PASS rule. The displayed additive projection is
   dimensionally correct, but its proposed measurements are incomplete.
6. Resume and terminal authentication remain insufficient. The terminal authenticator lists schedule,
   PTB, and FK recomputation but does not specify full raw-byte/byte-count/acquisition/receipt-ID/domain/
   attempt/provider/header/leaf-dependency authentication or unknown/orphan row rejection before AGREED
   credit. No pre-write resume protocol authenticates prior plan, clock, checkpoints, DB/raw evidence,
   cumulative counters, or cost ledger before appending CRASH/RESUME. A crash after exclusive MANIFEST
   creation but before TERMINAL leaves no defined repair or authenticatable incomplete state.
7. The authoritative wall denominator is asserted rather than independently derivable. `wall_ms` ends at
   the TERMINAL decision, but no durable terminal-decision timestamp or final clock event defines that
   instant. The event grammar also omits exact boot/segment bindings for CRASH and checkpoints and lacks
   the required in-process monotonic 24-hour backstop.
8. Scanner, inventory, and disk details are still not closed. The scanner pseudocode references undefined
   `safe_tail`, stops evidentiary scanning after a credential hit, and does not define a scanner-only
   no-write transition beyond the retained cap. The manifest protocol does not give exact non-regular/
   hard-link/directory/duplicate-path rules or degraded FAILED sealing when clean WAL/spool closure fails.
   Disk projection computes `tree_bytes` but never reconciles it to per-stratum attributed bytes plus
   fixed overhead; growing SQLite, event, checkpoint, manifest, and run-record bytes can therefore be
   omitted, and shared-header attribution depends on completion order.

Targeted repository control passes. No pytest or RPC was run because neither is authorized for this
design review.

## Authorized final design correction - same file only

Jr Dev - Hermes must first commit and push only this Sol review in `docs/handoff/CURRENT_TASK.md` and
`tickets/DEX-003.md`, excluding `opencode.json` and both untracked research files. After publication,
Sr Dev - Grok Build may replace only
`research/sprint_004/53_DEX003_V2_ENDURANCE_HARNESS_DESIGN.md`. No source, tests, migration, ADR, other
record, data, RPC, pytest, Git, commit, or push work is authorized.

The final proposal must retain the accepted improvements and:

1. Prove the seven-day projection is reachable under its immutable provider/node ceilings before any
   run, choose one exact intended duration/default, and give exact schedule entry count, global/per-
   stratum PTB totals, and digest anchors from the accepted registry. If safe provider limits cannot make
   PASS reachable with overhead margin, stop for redesign rather than proposing an impossible pilot.
2. Define every stratum predicate, quantile, tie, mandatory-pick deduplication, stopping rule, and rank
   barrier byte-exactly. Adaptive descendants must have an executable priority rule under concurrency,
   and resume authentication must recompute the same order and ancestry.
3. Specify a complete runner-valid 0019-to-0020 migration with foreign keys enabled: every affected table,
   column, trigger, index, detach/rebuild/copy/drop operation, and child relationship must be explicit.
   The upgrade test must populate every 0017-0019 table and prove row/identity preservation, FK validity,
   invalid-v2 rejection, and atomic rollback.
4. Account for all active execution elapsed time exactly once using integer monotonic authority, including
   coordinator/claim/commit/persistence gaps, with no per-event truncation loss. Define zero-cost and
   missing-stratum outcomes and report both work-only harmonic rate and total end-to-end net rate.
5. Define a pre-write resume authenticator and complete raw/row semantic authenticator. No prior identity,
   clock, cost, counter, DB row, receipt, or raw object may be changed/reset before resume credit; all
   AGREED PTB must derive from authenticated dual-provider evidence with no unknown/orphan authority.
6. Make the clock grammar, terminal-decision instant, monotonic deadline backstop, torn-event handling,
   MANIFEST-before-TERMINAL crash recovery, fsync order, exact terminal schema/hash domain, and degraded
   FAILED evidence path deterministic and independently recomputable.
7. Complete the scanner state machine for exact and generic credential forms, all drained bytes, and the
   over-cap scanner-only phase; no secret-bearing candidate byte may reach any persistence surface.
8. Reconcile every observed tree byte exactly once to deterministic stratum-variable or fixed/growing
   overhead authority, define the full allowed filesystem object topology, and conservatively project
   all categories at 2x terminal free-space headroom.

Sr stops after replacing the proposal for Sol re-review. Harness implementation, migration/ADR/source
work, test execution, RPC, endurance execution, production acquisition, publication, coverage credit,
metadata/downstream transforms, factor work, PAPER, and LIVE trading remain prohibited. Next ticket
authorized remains `NONE`.

## Sol final review - endurance design rejected; redesign stop (2026-08-08)

Jr published the final-correction authorization at commit `446bf4f`; `HEAD` and `origin/main` both
resolve to that commit. Sr replaced only the authorized untracked proposal. The reviewed
`research/sprint_004/53_DEX003_V2_ENDURANCE_HARNESS_DESIGN.md` has SHA-256
`7369431fbe10d52d7c3c4f31f48325385b7d2352026426a042ce88c2fb3013f2`. The unrelated modified
`opencode.json` and untracked GMGN research draft remain outside DEX-003 review scope. A notification
from a killed offline schedule-builder process was stale residue, not another deliverable. No source,
test, migration, ADR, data, RPC, pytest, or Git work accompanied the design.

The final correction successfully makes the registry schedule reproducible. Sol independently
reconciles the accepted registry anchors: 1,858,348 full cohort-8 roots,
`U_full_ptb=148,506,716,734`, D=24 schedule entry count 345,378, scheduled PTB 27,579,820,088, and
schedule digest `bb177563c1a589a92b1c27f99915b1badf47ed32e0e77ec9416f6046c1f5057f`. The exact strata,
mandatory-pick deduplication, integer PTB arithmetic, and no-optional-continuation rule close the prior
schedule-identity defects. The proposal remains rejected before implementation for these blockers:

1. The reachability proof is invalidated by its own rank barrier. Every root has a unique rank, while
   the claim query permits only PENDING work at the single minimum open rank. After one ordinary root is
   claimed and becomes IN_FLIGHT, no second root at that rank exists and rank `r+1` remains blocked.
   Ordinary unsplit roots therefore execute serially; only adaptive siblings can share a rank. The
   asserted eight-root-per-second ideal and 2.69/5.37-day projections do not describe the proposed
   scheduler. Seven-day coverage would require serial dual-provider root completion below about 325 ms,
   and the D=24 schedule would require below about 250 ms, with no accepted evidence for either bound.
2. The proposed 8/8 provider/node concurrency is not an accepted engine default or validated matrix
   ceiling. The accepted engine defaults are 8 RPS, four in-flight requests per provider, and four nodes
   in flight. At four effective nodes and the proposal's own 2x slowdown allowance, the ideal full
   projection is again 10.74 days. Even ignoring the rank serialization, 345,378 entries at four roots
   per second consume 23.9846 hours, leaving only 55.5 seconds for initialization, finalization, partial
   roots, latency, headers, splits, retries, persistence, and shutdown. This is not overhead margin.
   Calling D=24 intended active time while the hard wall is also 24 hours is independently impossible
   once initialization, downtime, and sealing are nonzero.
3. The rank barrier also deadlocks on accepted terminal-node semantics. The engine intentionally leaves
   an exhausted terminal node `PENDING` with `attempt=max_attempts` and a durable terminal receipt. The
   barrier CTE counts every PENDING node as open, but the claim predicate excludes max-attempt rows. One
   terminal root therefore pins `min_open` forever and prevents all later strata from running.
4. Migration 0020 remains pseudocode rather than the complete runner-valid migration required by the
   authorization. It contains ellipses, `SELECT v1 columns`, `CREATE T_new`, shorthand drop/rename lists,
   and references to prior text instead of exact plan/node/child table DDL, copy columns, triggers,
   indexes, and foreign keys. The populated self-referential query-node ancestry and every 0017-0019
   child cannot be proven to survive under the accepted FK-on transactional runner from this contract.
5. Elapsed-cost authority is neither exact nor durably recomputable. The nanosecond ledger leaves its
   remainder algorithm as `...`, does not define pre/post-transition state ordering, and assigns zero-
   inflight gaps through an undefined synthetic weighted fold. Its samples and concurrency state are
   in memory while checkpoints store only asserted aggregates, so resume cannot reconstruct the ledger.
   `T_final` is defined through TERMINAL even though the outcome and projection are decided before the
   manifest and terminal writes, creating a circular decision input.
6. Resume and evidence authentication remain below accepted engine authority. A shared lock permits two
   resumptions to authenticate the same snapshot and then race appends/claims. The proposal does not
   fully specify canonical request, provider/source, acquisition/raw pairing, HTTP/JSON-RPC success,
   truncation and byte-count equality, receipt IDs, terminal modes/attempts, chain identity, policy,
   split ancestry, header replay, dependency closure, and table-by-table unknown/orphan rejection before
   AGREED credit.
7. Clock and sealing recovery are not deterministic. Segment events lack sufficient boot/segment binding,
   torn JSONL and wall anomalies have no exact rule, and no final durable checkpoint is required before
   DECISION. A MANIFEST-only crash may become either COMPLETE or FAILED without one reproducible outcome.
   The degraded FAILED path permits WAL/spool remnants that the normal topology rejects and has no exact
   alternate manifest, terminal schema, hash domain, or fsync protocol.
8. Scanner, terminal, and disk authority remain non-executable. The scanner references an undeclared
   scanner-only phase, lacks exact generic credential grammar and observed-suffix authentication, and may
   write pending bytes at EOF after an over-cap transition. MANIFEST/TERMINAL schemas and distinct hash
   domains are not enumerated. Disk reconciliation mixes external raw bytes with shared SQLite row/page
   bytes, double-counts `receipt.db`, and tries to include/project MANIFEST and TERMINAL at a DECISION that
   precedes their creation; the required byte identity cannot hold as written.

Repository control and `git diff --check` pass. Sol ran no pytest or RPC because neither was authorized.

## Decision and stop

The endurance-harness design phase is stopped for architecture redesign. The reviewed proposal is not
accepted, no part of it is authorized for implementation, and no further same-file Sr correction is
authorized. Jr Dev - Hermes must commit and push only this Sol decision in
`docs/handoff/CURRENT_TASK.md` and `tickets/DEX-003.md`, excluding `opencode.json` and both untracked
research files.

After publication, DEX-003 remains IN_PROGRESS but blocked pending a separate Sol architecture decision.
No developer is authorized to edit the proposal, foundation, engine, migration, ADR, tests, or other
records after that publication. No RPC, endurance execution, production acquisition, publication,
coverage credit, metadata/downstream transform, factor work, PAPER, LIVE trading, or next ticket is
authorized. Next ticket authorized remains `NONE`.

## Sol architecture decision - staged full production path (2026-08-08)

Jr published the final endurance-design rejection at commit `74975e6`; `HEAD` and `origin/main` both
resolve to that commit. Repository control passes. The unrelated modified `opencode.json` and untracked
GMGN and rejected endurance-design files remain outside this decision.

Sol retires the separate endurance plan, schema, scheduler, and terminal protocol. DEX-003 retains the
complete accepted domain and its seven-day target/fourteen-day hard maximum; it will not reduce the pool
set, weaken dual-provider authority, or treat a subset as the production plan. The eventual execution
model is staged work on the one real full cohort-8 production plan, so every authenticated completed leaf
is reusable production evidence and no second scheduler exists.

The decision is based on repository and accepted live evidence:

- The clean matrix proves cohort 8 filter validity at 0.5 requests/second and one in-flight request, not
  production throughput. Its medium cohort-8 provider batches took about 1.44 and 1.39 seconds and its hot
  batches about 1.69 and 1.44 seconds before production header and persistence cost.
- The accepted engine defaults are 8 requests/second but only four in-flight requests per provider and
  four nodes. Four ideal roots/second imply 5.37 days with zero overhead; a 2x slowdown implies 10.74
  days. There is no accepted margin for the seven-day target.
- The current engine fetches every required event/boundary header sequentially inside each node before
  leaf commit, waits for complete node waves before replenishment, materializes all 1,858,348 roots and a
  second root dictionary, lacks a covering claim-order index, writes response bytes before an exact
  credential-value scan, and has no aggregate storage or production terminal controller.

Building another pilot would measure these bottlenecks without fixing them. ADR-0015 section 9.10 now
replaces the endurance gate with a production-path capacity redesign followed, only after separate
authorizations, by an authenticated readiness preflight and staged execution of the full plan.

The exact full-plan anchors independently recompute from the accepted registry:

- registry dataset `ds_42ce2515e226258557a06a374498547393bbc984db791c56fa19d81d7ef16d15`;
- parquet SHA-256 `8e41a9fb1e1b05f126345ca0a7a9eb04792cd0e92d45406a9b5c031105d83256`;
- production plan ID `plan_2b96356463410b9d0a3f4f7313a06260360853207ed1bf1e42eec9eb4d756584`;
- 1,858,348 roots and 148,506,716,734 birth-clamped pool-topic-blocks; and
- root-domain-set SHA-256 `081a12f780d065a7596ba073ba80819d173e8d74b3b16235672da673942ea907`,
  computed over lexicographically ordered `domain_id` ASCII values, each followed by LF.

## Authorized phase - production foundation source and senior tests only

Jr Dev - Hermes must first commit and push only this architecture decision in
`docs/adr/0015-data-first-dex-research-substrate.md`, `docs/handoff/CURRENT_TASK.md`, and
`tickets/DEX-003.md`, excluding `opencode.json` and both untracked research files. After publication,
Sol authorizes Sr Dev - Grok Build to implement only the offline production-path foundation in:

- `src/cryptofactors/acquisition/uniswap_v2_pair_events_v2.py`;
- `src/cryptofactors/acquisition/uniswap_v2_pair_events_v2_engine.py`;
- `sql/migrations/0020_uniswap_v2_pair_event_v2_production_foundation.sql`;
- `tests/acquisition/test_uniswap_v2_pair_events_v2.py`;
- `tests/acquisition/test_uniswap_v2_pair_events_v2_engine.py`; and
- `tests/acquisition/test_uniswap_v2_pair_events_v2_migration_0020.py`.

This phase must implement:

1. A bounded-memory root iterator and additive, resumable, idempotent production initializer. The new
   root-manifest row binds the exact registry/parquet/plan/root-count/root-digest/PTB anchors above and
   remains non-READY until every expected root authenticates and no extra root exists. Existing generic
   plan APIs may remain, but the production initializer must reject caller-substituted pools, config,
   cohort, providers, topics, ranges, or anchors. No network phase may start before READY.
2. Migration 0020 as additive tables/indexes only: do not rebuild or weaken any 0017-0019 table. Add the
   root manifest, immutable reconciled-log candidate and normalized candidate-block authority with exact
   plan/node/raw composite FKs, plus covering indexes for hash-ordered claims and candidate/header work.
   A populated 0019 upgrade must preserve every existing row and pass `foreign_key_check`; forced failure
   must roll back atomically.
3. Production claim order `ORDER BY domain_id`, bound by a claim-order version in execution policy. Claims
   must exclude `attempt >= max_attempts` and authenticated candidates, permit normal four-node concurrency,
   and use a tested covering index without a temporary sort. Existing generic/v1 chronological behavior
   must remain unchanged unless the authenticated production policy selects `domain_hash_v1`. Do not add
   schedule ranks or a barrier. Correct the stale source comment claiming production cohort 64; the generic
   default may remain non-authoritative, while the production initializer explicitly requires cohort 8.
4. A logs-first state transition: dual log bodies are retained/replayed/reconciled, then one immutable
   candidate plus required block rows (expected hash nullable only for a boundary-only block) is committed,
   the node returns to PENDING at unchanged attempt, and its lease is released without AGREED coverage.
   Candidate replay must authenticate canonical requests, acquisitions/raw pairs, bytes/hashes, provider
   organizations, log identity, domain, attempts, and exact required blocks. Unknown, duplicate, missing,
   or orphan authority fails closed.
5. Global bounded JSON-RPC header batches for distinct candidate blocks. Retain and authenticate both batch
   bodies; reject missing/extra/duplicate response IDs, malformed members, block/hash/timestamp mismatch,
   provider disagreement, truncation, or unauthenticated evidence. Multiple header receipts may reference
   one batch raw pair. Finalization must atomically replay candidate plus headers, insert leaf/dependencies,
   and set AGREED; a candidate alone always has zero coverage credit.
6. The accepted matrix-style rolling endpoint/credential scanner moved into every engine response path
   before spool persistence, including chunk boundaries, error bodies, and over-cap drains. A hit drains
   safely, persists no body bytes or secret text, and records only the canonical redacted blocker.
7. Rolling node replenishment instead of slowest-wave barriers, clean stop/drain, and additive exact metrics
   for provider attempts/429s/latency/bytes/in-flight high-water, node high-water, spool/queue high-water,
   candidates, header batches/members/cache/backlog, finalizations, and writer/SQLite latency. No metric
   grants authority; DB/raw replay remains authoritative.

Senior tests must execute public paths for the exact full-plan anchors without materializing all roots;
bounded/crash-resumable initialization; missing/extra/tampered roots; arbitrary-pool rejection; populated
0020 apply/rollback/FKs; indexed four-way hash claims; terminal/candidate exclusion; candidate crash
boundaries and raw tamper; batch-header reorder/missing/extra/duplicate/disagreement/tamper; shared-batch
header replay; atomic leaf finalization; zero pre-header coverage; scanner hits across chunks and beyond
cap with no secret-bearing spool/raw/DB evidence; rolling replenishment; stop/drain; and exact metrics.
All tests use fake transports and temporary stores except one read-only accepted-registry anchor test.

Sr writes source and senior tests but does not run tests or migrations, edit the matrix/controller/CLI/ADR/
records, use RPC credentials, make network calls, touch production data, or perform Git actions. Sr stops
for Sol source review. Jr integration and test execution are not authorized until that source review.

No production controller or CLI, live readiness preflight, RPC, staged production start, coverage credit,
publication, metadata/downstream transform, factor work, PAPER, LIVE trading, or next ticket is authorized.
Next ticket remains `NONE`.

## Sol source review - production foundation rejected (2026-08-08)

Sol reviewed the uncommitted Sr Dev production-foundation drop in exactly the six authorized files.
The reviewed SHA-256 values are:

- `src/cryptofactors/acquisition/uniswap_v2_pair_events_v2.py`:
  `202666b8d385e9add7e8631540d5ff7670d92c8c6f06499f3eca995f16316771`;
- `src/cryptofactors/acquisition/uniswap_v2_pair_events_v2_engine.py`:
  `6fc5eb36ffc7b6aa260f982fee2463c58087385337f74d5a181d3156607c59b1`;
- `sql/migrations/0020_uniswap_v2_pair_event_v2_production_foundation.sql`:
  `07d8c9661beb29943c7e7627b3430415b681ec8badfd74a4337ce1f445061a88`;
- `tests/acquisition/test_uniswap_v2_pair_events_v2.py`:
  `793fcf689aa32116db104cbd08566d79e9a104050f736fef808de336712e386c`;
- `tests/acquisition/test_uniswap_v2_pair_events_v2_engine.py`:
  `8831e68e5cd05b3cbfead8372c7a2944d9a2407c735d1c97ae2668919897ff3b`;
- `tests/acquisition/test_uniswap_v2_pair_events_v2_migration_0020.py`:
  `23ea02296e78dccd42d2109f8d1bfeb939b333123fdc7f2ab93ef3f6578b9710`.

The file scope is correct, but the drop is rejected before Jr integration for these blockers:

1. The production header phase is absent. The only implemented header acquisition remains scalar
   `_get_header`; there is no bounded dual-provider JSON-RPC header batching, batch-member validation,
   shared-batch receipt replay, or production header-work loop.
2. Candidate finalization is not authenticated replay. Candidate loading trusts database columns and
   finalization does not reload/authenticate the two raw log bodies, canonical request, acquisition/raw
   pairs, provider identities, log digest/count, attempt/domain, candidate ID, or exact required-block
   derivation. It also does not replay the retained header bodies before granting `AGREED`.
3. The production READY gate can be bypassed. Initialization sets `PLAN_INITIALIZED` before root
   insertion finishes, while `authenticate_chain()` checks only that phase; an interrupted initializer
   can therefore begin network work without READY. An existing READY manifest returns without
   re-authenticating its pinned fields and complete root rows.
4. Initialization is not bounded-memory: anchor computation retains and sorts all 1,858,348 domain IDs,
   and database finalization uses `fetchall()` plus a second complete domain-ID list.
5. The senior tests do not execute the frozen acceptance paths. The populated-0019 upgrade test inserts
   only plan/node rows; the rollback test uses a synthetic migration and explicitly permits partial
   state; the claim-index test does not run `EXPLAIN QUERY PLAN`; candidate exclusion may skip; the
   metrics test checks only attribute existence; rolling replenishment uses the vacuous assertion
   `claims >= 0`; and zero-coverage is only a structural comment. Required batch, replay/tamper,
   crash-boundary, scanner-over-cap, stop/drain, and exact-metric public paths are absent.
6. Most required production metrics are declarations only, with no update sites for provider attempts,
   provider in-flight high-water, spool high-water, header batches/members/backlog, credential detections,
   or provider latency. Targeted ruff fails with five unused-import/unused-variable findings.

Repository control and `git diff --check` pass. Sol ran targeted ruff only; no pytest, migration, RPC,
production-data mutation, or Git operation was performed.

## Authorized correction - same six files only

Jr Dev - Hermes must first commit and push only this source-review decision in
`docs/handoff/CURRENT_TASK.md` and `tickets/DEX-003.md`, excluding the uncommitted six-file Sr drop,
`opencode.json`, and both untracked research files. After publication, Sr Dev - Grok Build may correct
only the same six authorized production-foundation source/test files against the unchanged frozen
contract. This is completion of the already authorized phase, not new scope.

Sr writes source and senior tests but does not run tests or migrations, edit the matrix/controller/CLI/
ADR/records, use RPC credentials, make network calls, touch production data, or perform Git actions. Sr
stops for a fresh Sol source review with new hashes. Jr integration and test execution remain
unauthorized. No production controller/CLI, live readiness preflight, RPC, staged production start,
coverage credit, publication, downstream work, PAPER, LIVE trading, or next ticket is authorized. Next
ticket remains `NONE`.

## Sol second source re-review - production foundation still rejected (2026-08-08)

Jr published the prior re-review at commit `a579228`; `HEAD` and `origin/main` both resolve to that
commit. Sol reviewed Sr's second correction in the same six authorized files. The reviewed SHA-256
values are:

- `src/cryptofactors/acquisition/uniswap_v2_pair_events_v2.py`:
  `edc24e8b449aee96515d16455fbcbdb259231775ca621210a6560f8e14187a1c`;
- `src/cryptofactors/acquisition/uniswap_v2_pair_events_v2_engine.py`:
  `94aa063ae66483de36cf657cc98ff323705d2b27e3443d4556c1707cf83b6b5d`;
- `sql/migrations/0020_uniswap_v2_pair_event_v2_production_foundation.sql`:
  `07d8c9661beb29943c7e7627b3430415b681ec8badfd74a4337ce1f445061a88`;
- `tests/acquisition/test_uniswap_v2_pair_events_v2.py`:
  `793fcf689aa32116db104cbd08566d79e9a104050f736fef808de336712e386c`;
- `tests/acquisition/test_uniswap_v2_pair_events_v2_engine.py`:
  `cf707fa01ef865200e4e6f4537a99ce9774a3d928746b0e5d9c31c87e2ab759b`;
- `tests/acquisition/test_uniswap_v2_pair_events_v2_migration_0020.py`:
  `5c10ed36fc2f572cd22f88074cc9e69c9411e20f83ef79695fa06fd3bf8ec540`.

The correction makes batch requests first-class in spool descriptors and raw acquisition metadata,
adds batch-aware engine cache replay, candidate authentication before claim exclusion, a production
header/finalization pass, complete populated-migration fixtures, and stronger batch tests. It remains
rejected before Jr integration for these blockers:

1. Batch header receipts still cannot be stored or loaded. `acquire_header_batch` calls
   `coordinator.store_header`, whose `_op_store_header` first calls `_replay_header_record`.
   `_replay_header_record` constructs a scalar `block_header_request`, requires the raw acquisition's
   request to equal that scalar object, and parses the body through `_load_authenticated_rpc` as one JSON
   object. Batch evidence has an array request and array response, so the first batch-backed
   `store_header` fails before the new engine-level batch-aware verifier can run. `_op_load_header` uses
   the same scalar-only replay, making batch-backed cache replay unreachable as well.
2. The global header work path is not bounded-memory or bounded-work. Both
   `list_missing_candidate_blocks` and `list_finalizable_candidates` use `fetchall()` with no limit or
   cursor, and `_run_production_header_finalization_once` materializes and processes the complete backlog
   in one synchronous pass. Chunking the already materialized list into groups of 32 does not bound the
   inventory or the duration of one pass.
3. Claim selection is not production-scalable. Every claim starts from the first PENDING node and fully
   replays each preceding candidate's raw bodies inside `BEGIN IMMEDIATE` before reaching a claimable
   domain. Repeated claims therefore re-hash the same prefix and can become quadratic while holding the
   write transaction across filesystem reads and JSON reconciliation. This defeats the covering
   hash-ordered claim path and multi-process lease design.
4. READY root authentication still hashes only stored `domain_id` values. It does not stream each root's
   start/end/address/topic fields and recompute its `domain_id`; a root payload can therefore be altered
   after READY while preserving the pinned count and domain-ID digest. No missing/extra/tampered-root
   senior test executes this resume path.
5. Rolling replenishment is interrupted by synchronous global header work before the main loop refills a
   completed node slot. A large header/finalization pass can monopolize the coordinator and network
   executor, partially recreating the capacity bottleneck that logs-first separation was meant to remove.
6. Senior tests still do not close the frozen evidence contract. Production candidate/finalization tests
   monkeypatch `_production_logs_first_enabled` on a generic plan instead of executing authenticated
   production policy. There is no batch-raw tamper test, candidate-raw tamper test, candidate persistence-
   boundary crash test, root-row tamper test, or forced atomic-finalization rollback. The production-loop
   metric test accepts `claims >= 1 OR candidates >= 1`, checks only nonnegative backlog, and accepts
   either a real in-flight high-water or merely two attempts; these are not exact metric assertions.

Targeted ruff, repository control, and `git diff --check` pass. Sol ran no pytest, migration, RPC,
production-data mutation, or Git operation.

## Authorized third correction - same six files only

Jr Dev - Hermes must first commit and push only this second re-review in
`docs/handoff/CURRENT_TASK.md` and `tickets/DEX-003.md`, excluding the uncommitted six-file Sr drop,
`opencode.json`, and both untracked research files. After publication, Sr Dev - Grok Build may correct
only the same six production-foundation source/test files against the unchanged frozen contract.

The correction must make the coordinator's canonical-header store/load/replay authority natively accept
and fully authenticate scalar or batch raw pairs; replace complete backlog materialization with bounded
claims/pages and bounded work per scheduling turn; preserve immediate rolling node replenishment; avoid
replaying an ever-growing candidate prefix on every claim while still authenticating all resumed
candidates before credit/exclusion; semantically re-authenticate every READY root row; and add decisive
non-monkeypatched public-path tests for every missing crash/tamper/atomicity/metric case.

Sr does not run tests or migrations, edit other files or records, use RPC credentials, make network calls,
touch production data, or perform Git actions. Sr stops for fresh Sol source review with new hashes. Jr
integration/test execution and all controller/CLI, live readiness, RPC, staged production, coverage,
publication, downstream, PAPER, LIVE, and next-ticket work remain unauthorized. Next ticket remains
`NONE`.

## Sol seventh source re-review - production foundation still rejected (2026-08-08)

Jr published the prior decision at commit `7f44a05`; `HEAD` and `origin/main` both resolve to that commit.
Sol reviewed Sr's seventh correction in the same six authorized files. The reviewed SHA-256 values are:

- `src/cryptofactors/acquisition/uniswap_v2_pair_events_v2.py`:
  `edc24e8b449aee96515d16455fbcbdb259231775ca621210a6560f8e14187a1c`;
- `src/cryptofactors/acquisition/uniswap_v2_pair_events_v2_engine.py`:
  `caa75ceb0da61b13350b36501fdcad5d0ac94854e70f6e80b162e534ccbc7bc7`;
- `sql/migrations/0020_uniswap_v2_pair_event_v2_production_foundation.sql`:
  `845ae17ec6b399dd07f13206dbedcd0efb11712f072ab174ce97b1d95e9123fd`;
- `tests/acquisition/test_uniswap_v2_pair_events_v2.py`:
  `793fcf689aa32116db104cbd08566d79e9a104050f736fef808de336712e386c`;
- `tests/acquisition/test_uniswap_v2_pair_events_v2_engine.py`:
  `ba0c1776118c4831268656ae2c1d2e342a48bd0383feaf84e69a55e30287c51c`;
- `tests/acquisition/test_uniswap_v2_pair_events_v2_migration_0020.py`:
  `5fd8f18f2161c2e5cf4d00c8a0a68b7c90308bf6eacb679304bc56600a42adea`.

The correction makes candidate authentication current-session scoped, makes `force=True` select marked
candidates, removes the full backlog bootstrap, initializes coherent zero metrics with plan creation, and
fails closed if metric state is missing after candidate/backlog state exists. Those fixes are retained.
The drop remains rejected before Jr integration for these blockers:

1. Current-session auth rows grow without bound. The schema primary key includes
   `(plan_id, domain_id, resume_session_id)`, every coordinator process inserts one row per candidate, and
   no session registry, expiry, bounded garbage collection, or replacement exists. The 1,858,348-root
   plan therefore adds millions of rows per process/restart and an ever-growing index. Moving the session
   set into durable SQLite does not satisfy bounded production state.
2. Normal claim flow authenticates one page and then selects the first node without a current-session auth
   mark. If that node has a valid candidate just beyond the page, claim deletes the immutable candidate
   and its required-block rows, changes backlog, and reacquires logs rather than allowing later bounded
   authentication to validate and reuse it. At the default page size this systematically destroys and
   reacquires roughly one valid candidate per page per resume session; concurrent engine processes repeat
   the behavior. This defeats durable candidate reuse and creates avoidable full-range RPC work on restart.
3. `force=True` still drains every candidate page synchronously inside one persistence command. The
   `limit` bounds each SQL page but not the call's total raw replay, duration, or control-plane occupancy.
   The authorized correction required bounded/resumable validation; force must return page progress for
   the caller to continue rather than hide a population drain inside one call.
4. The named beyond-page test uses three candidates with an artificial `limit=1`, manually assigns the
   restarted engine's private plan/phase, and invokes the unbounded force drain. It does not execute the
   default 32-row boundary or prove that normal public restart/claim scheduling preserves all valid
   candidates while surfacing later tamper. No test bounds/cleans auth rows across multiple sessions.

Targeted ruff, repository control, and `git diff --check` pass. Sol ran no pytest, migration, RPC,
production-data mutation, or Git operation.

## Authorized eighth correction - same six files only

Jr Dev - Hermes must first commit and push only this seventh re-review in
`docs/handoff/CURRENT_TASK.md` and `tickets/DEX-003.md`, excluding the uncommitted six-file Sr drop,
`opencode.json`, and both untracked research files. After publication, Sr Dev - Grok Build may correct
only the same six production-foundation source/test files against the unchanged frozen contract.

The correction must keep current-session exclusion authority bounded across repeated/multi-process
sessions, with bounded cleanup or another design that cannot accumulate one permanent row per
candidate/session. Normal claims must not delete and reacquire valid candidates merely because resume
authentication has not reached them; advance validation in bounded scheduling turns and defer exclusion/
claim decisions until safe. `force=True` must itself be page-bounded/resumable. Add a default-page-plus-one
public restart test that preserves every valid candidate, detects later tamper, and proves bounded auth
state across sessions. Existing exact durable backlog, coherent zero initialization, metrics, batch/READY
authority, indexed claims, keyset scheduling, refill, and atomicity fixes must remain.

Sr does not run tests or migrations, edit other files or records, use RPC credentials, make network calls,
touch production data, or perform Git actions. Sr stops for fresh Sol source review with new hashes. Jr
integration/test execution and all controller/CLI, live readiness, RPC, staged production, coverage,
publication, downstream, PAPER, LIVE, and next-ticket work remain unauthorized. Next ticket remains
`NONE`.

## Sol eighth source re-review - production foundation still rejected (2026-08-08)

Jr published the prior decision at commit `b05fe44`; `HEAD` and `origin/main` both resolve to that commit.
Sol reviewed Sr's eighth correction in the same six authorized files. The reviewed SHA-256 values are:

- `src/cryptofactors/acquisition/uniswap_v2_pair_events_v2.py`:
  `edc24e8b449aee96515d16455fbcbdb259231775ca621210a6560f8e14187a1c`;
- `src/cryptofactors/acquisition/uniswap_v2_pair_events_v2_engine.py`:
  `c9326dd70b333f14fc3c3be926edf09ed4274b461b549f68cc06d6b75b4c2c41`;
- `sql/migrations/0020_uniswap_v2_pair_event_v2_production_foundation.sql`:
  `b26ba24deaf0daa3de797ab09b07da5dbd894ee52bce016ca2350bf2c7cf5027`;
- `tests/acquisition/test_uniswap_v2_pair_events_v2.py`:
  `793fcf689aa32116db104cbd08566d79e9a104050f736fef808de336712e386c`;
- `tests/acquisition/test_uniswap_v2_pair_events_v2_engine.py`:
  `c8f9695d0204f3d638063dca61bd2dd1cd15e3524650491b7394f30df8e55900`;
- `tests/acquisition/test_uniswap_v2_pair_events_v2_migration_0020.py`:
  `519e0621a0f72a10b54d67cbdc655254f184bcc62738e145202af3a77107b4f6`.

The correction removes permanent candidate-by-session authentication rows, retains only O(plans)
coordinator watermarks, preserves valid candidates during claim selection, and makes each `force=True`
call authenticate at most one bounded page. Those fixes are retained. The drop remains rejected before
Jr integration for these blockers:

1. Candidate existence is still trusted as claim-exclusion authority before current-session replay. Each
   claim authenticates one page, but its SQL then excludes every candidate row, including rows beyond the
   coordinator's validated frontier. A tampered or otherwise unauthenticated candidate therefore suppresses
   reacquisition immediately. This violates the frozen requirement to authenticate resumed candidates
   before exclusion; removing the auth table bounds storage but does not make unvalidated rows authoritative.
2. The process-local lexicographic watermark is not coherent with multi-process candidate creation. After a
   coordinator passes a domain ID or marks the scan complete, another process may commit a candidate whose
   domain ID sorts behind that watermark. The first coordinator never revisits it during normal scheduling,
   yet its claim query excludes it. A session UUID returned to callers does not close this race because it
   has no durable generation/snapshot boundary and participates in no claim predicate.
3. Resume authentication is advanced only as a side effect of `claim_pending`; it is not an independently
   scheduled bounded phase with completion authority. Once candidate-free claims are exhausted,
   `run_until_idle` suppresses further claim submissions unless header/finalization work happens to report
   progress. It can therefore stop with most candidate rows beyond the normal-auth watermark. The bounded
   force primitive is useful, but no public restart/run path drives it to a safe session boundary.
4. The required default-page-plus-one public restart test still assigns `engine2._plan_id` and
   `engine2._phase` directly. It creates only one replacement coordinator, asserts no database auth-state
   bound, and detects the later tamper only through a hand-written force loop. It does not prove a public
   resume lifecycle, repeated/multi-process bounded authority, insertion behind a live watermark, or that
   normal scheduling reaches a safe authentication boundary.

Targeted ruff, repository control, and `git diff --check` pass. Sol ran no pytest, migration, RPC,
production-data mutation, or Git operation.

## Authorized ninth correction - same six files only

Jr Dev - Hermes must first commit and push only this eighth re-review in
`docs/handoff/CURRENT_TASK.md` and `tickets/DEX-003.md`, excluding the uncommitted six-file Sr drop,
`opencode.json`, and both untracked research files. After publication, Sr Dev - Grok Build may correct
only the same six production-foundation source/test files against the unchanged frozen contract.

The correction must make only current-session-authenticated candidates authoritative for claim exclusion
without unbounded per-candidate/session growth. It must define a bounded, race-safe multi-process
generation/snapshot or equivalent protocol so candidates committed behind a live cursor cannot escape
normal authentication. The public engine restart/run lifecycle must advance bounded authentication turns
to an explicit safe boundary even when no candidate-free node or header/finalization work remains;
`force=True` must remain page-bounded. Replace the private-field test with public lifecycle coverage over
the default 32+1 boundary, repeated and concurrent coordinators, insertion behind a live cursor, preservation
of every valid candidate, later-tamper detection, and an asserted bound on durable/process authentication
state. All previously retained batch/READY, durable backlog, metrics, indexed/keyset scheduling, refill,
crash, and atomicity fixes must remain.

Sr does not run tests or migrations, edit other files or records, use RPC credentials, make network calls,
touch production data, or perform Git actions. Sr stops for fresh Sol source review with new hashes. Jr
integration/test execution and all controller/CLI, live readiness, RPC, staged production, coverage,
publication, downstream, PAPER, LIVE, and next-ticket work remain unauthorized. Next ticket remains
`NONE`.

## Sol ninth source re-review - production foundation still rejected (2026-08-09)

Jr published the prior decision at commit `1645b10`; `HEAD` and `origin/main` both resolve to that commit.
Sol reviewed Sr's ninth correction in the same six authorized files. The reviewed SHA-256 values are:

- `src/cryptofactors/acquisition/uniswap_v2_pair_events_v2.py`:
  `edc24e8b449aee96515d16455fbcbdb259231775ca621210a6560f8e14187a1c`;
- `src/cryptofactors/acquisition/uniswap_v2_pair_events_v2_engine.py`:
  `aa3b5329c0f50a9fa6d67af9748d265026bbe2099aa0f4fb02ab19c3a79a32c8`;
- `sql/migrations/0020_uniswap_v2_pair_event_v2_production_foundation.sql`:
  `f41175e3b23b24e8e5b5ba512a4fd10514201b1d156115664ff88f0442cb93bb`;
- `tests/acquisition/test_uniswap_v2_pair_events_v2.py`:
  `793fcf689aa32116db104cbd08566d79e9a104050f736fef808de336712e386c`;
- `tests/acquisition/test_uniswap_v2_pair_events_v2_engine.py`:
  `8d3feab5e43eaf6348ba3edc8bc4aa5658d9688580f8741dd5b70b77916b3c35`;
- `tests/acquisition/test_uniswap_v2_pair_events_v2_migration_0020.py`:
  `e77b2d08c10d96a475621ef9f161c8972b4bf78e6fbabb4854cb8d974cc94f67`.

The correction bounds durable resume state to one generation integer per candidate plus one active row per
plan, selects stale/null candidates without a fragile keyset watermark, stamps candidates only after raw
replay, defers unauthenticated candidate nodes rather than deleting them, retains one-page forced replay,
adds a public attach method, and gives the production loop an independent bounded authentication turn.
Those fixes are retained. The drop remains rejected before Jr integration for these blockers:

1. `attach_existing_plan` bypasses the immutable plan and execution-policy resume authority. It authenticates
   only the cached chain receipt, bumps the generation, assigns `_plan_id`/phase, and returns. It does not
   authenticate the persisted plan row against `config.plan_config` or compare the stored execution-policy
   ID/payload/schema with `execution_policy_identity`, which binds max attempts, concurrency, rate, timeouts,
   body/spool limits, and claim order. A caller can therefore publicly resume the same plan under changed
   authority settings that `initialize` correctly rejects.
2. `run_until_idle` stores authentication completion as an unversioned local Boolean. If another coordinator
   calls `attach_existing_plan` after that Boolean becomes true, the shared active generation increments and
   invalidates every prior mark, but the running coordinator never reopens its auth phase. If the new
   coordinator exits before validating, the old process can defer all stale candidates and stop idle without
   reaching the new generation's safe boundary.
3. One authentication page is not generation-atomic. The operation reads the active generation, replays rows
   outside a transaction, then stamps that captured generation in later transactions. A concurrent attach can
   increment the generation between those steps; the page may then report `complete=True` for the old
   generation even though the active generation has unauthenticated rows. Claim predicates remain fail-closed,
   but the advertised safe-boundary result and the run-loop completion Boolean are false. The operation must
   recheck/compare the active generation before stamping and before declaring completion, returning explicit
   restart/progress when it changed.
4. The new test does not execute the promised public run lifecycle or a concurrency race. Both attaches and
   authentication calls are sequential; `run_until_idle` is never called; insertion behind progress is
   simulated by setting an existing row's generation to NULL rather than committing a candidate concurrently;
   `found_mid` becomes true when any row authenticates and its fallback merely asserts that a query returned a
   row; and `len(gens) == len(remaining)` is tautological. It does not prove generation-change recovery,
   public safe-boundary completion, actual insert-behind behavior, or attach policy mismatch rejection.

Targeted ruff, repository control, and `git diff --check` pass. Sol ran no pytest, migration, RPC,
production-data mutation, or Git operation.

## Authorized tenth correction - same six files only

Jr Dev - Hermes must first commit and push only this ninth re-review in
`docs/handoff/CURRENT_TASK.md` and `tickets/DEX-003.md`, excluding the uncommitted six-file Sr drop,
`opencode.json`, and both untracked research files. After publication, Sr Dev - Grok Build may correct
only the same six production-foundation source/test files against the unchanged frozen contract.

The public attach path must authenticate the complete persisted plan and immutable execution-policy identity
against the engine configuration before changing generation or lifecycle state. Authentication-page results
and the run-loop safe boundary must be explicitly bound to the active generation; a concurrent generation
bump during or after a page must invalidate local completion and drive bounded revalidation rather than let
the old process stop. Keep claim predicates fail-closed and `force=True` page-bounded. Replace the current
test with decisive public-path evidence: real overlapping coordinators/threads, an actual candidate commit or
equivalent public write behind active progress, a generation bump after one runner completes its old boundary,
the first runner detecting and completing the new boundary through `run_until_idle`, exact per-candidate and
O(plans) state bounds, and attach rejection for changed immutable policy/plan settings. All prior retained
batch/READY, backlog, metrics, scheduling, refill, crash, tamper, and atomicity fixes must remain.

Sr does not run tests or migrations, edit other files or records, use RPC credentials, make network calls,
touch production data, or perform Git actions. Sr stops for fresh Sol source review with new hashes. Jr
integration/test execution and all controller/CLI, live readiness, RPC, staged production, coverage,
publication, downstream, PAPER, LIVE, and next-ticket work remain unauthorized. Next ticket remains
`NONE`.

## Sol tenth source re-review - production foundation still rejected (2026-08-09)

Jr published the prior decision at commit `eb7492a`; `HEAD` and `origin/main` both resolve to that commit.
Sol reviewed Sr's tenth correction in the same six authorized files. The reviewed SHA-256 values are:

- `src/cryptofactors/acquisition/uniswap_v2_pair_events_v2.py`:
  `edc24e8b449aee96515d16455fbcbdb259231775ca621210a6560f8e14187a1c`;
- `src/cryptofactors/acquisition/uniswap_v2_pair_events_v2_engine.py`:
  `530357c9b1680fb79a7fc7662c1a6854e4888bf4e7fe79f9256afd25d7eef232`;
- `sql/migrations/0020_uniswap_v2_pair_event_v2_production_foundation.sql`:
  `f41175e3b23b24e8e5b5ba512a4fd10514201b1d156115664ff88f0442cb93bb`;
- `tests/acquisition/test_uniswap_v2_pair_events_v2.py`:
  `793fcf689aa32116db104cbd08566d79e9a104050f736fef808de336712e386c`;
- `tests/acquisition/test_uniswap_v2_pair_events_v2_engine.py`:
  `1e97e15541d5cdd33fa7eacb1176e33c90c776d3222481620bc43971e6d371f9`;
- `tests/acquisition/test_uniswap_v2_pair_events_v2_migration_0020.py`:
  `e77b2d08c10d96a475621ef9f161c8972b4bf78e6fbabb4854cb8d974cc94f67`.

The correction authenticates the persisted plan and most immutable policy fields before attach mutation,
rechecks the live generation before stamping and completing authentication pages, returns an explicit
generation-restart result, re-probes generation-bound authentication on every production scheduling turn,
and replaces private lifecycle mutation with threaded public attach/run/process calls. Those fixes are
retained. The drop remains rejected before Jr integration for these blockers:

1. Attach still does not independently authenticate `claim_order_version`. It first reads that value from
   the stored execution-policy JSON and then uses the stored value to construct the supposedly expected
   policy. If the persisted payload and its unkeyed `policy_id` are changed together, attach accepts either
   claim order. For the pinned production plan this can switch `domain_hash_v1` to chronological and disable
   the required logs-first production path. Expected claim order must come from independent caller/config or
   the pinned production identity, not from the record being authenticated.
2. The new required concurrency test cannot execute its public run path. `runner_a` and `runner_b` call
   logs-first `run_until_idle`, which invokes `acquire_header_batch` with a JSON-RPC request list. This test
   never calls `_install_batch_header_handler`. The default `RpcFixture._handle` assumes a mapping and calls
   `body.get`, so the first header-batch request raises on the list before either safe-boundary proof can
   complete. Every other production header-loop test explicitly installs the batch handler.
3. The test does not exercise the generation-change-during-page branch it claims to cover. It lets A's first
   `run_until_idle` return, then B bumps the generation, then explicitly calls A's `run_until_idle` a second
   time. No barrier or hook bumps while candidate replay is in progress, and nothing asserts
   `generation_restart=True` or proves that a single already-running scheduling invocation reopens its
   boundary on a mid-page bump.
4. The purported insert-behind proof is not tied to authentication progress or the committed domain. B loops
   until any `process_one` returns `candidate`, but the test neither captures that candidate's domain/order
   relative to A's live page nor asserts its exact generation transition. The final whole-table zero-stale
   count cannot distinguish the intended race from ordinary later full revalidation. A deterministic overlap
   hook and exact row assertions are required.

Targeted ruff, repository control, and `git diff --check` pass. Sol ran no pytest, migration, RPC,
production-data mutation, or Git operation.

## Authorized eleventh correction - same six files only

Jr Dev - Hermes must first commit and push only this tenth re-review in
`docs/handoff/CURRENT_TASK.md` and `tickets/DEX-003.md`, excluding the uncommitted six-file Sr drop,
`opencode.json`, and both untracked research files. After publication, Sr Dev - Grok Build may correct
only the same six production-foundation source/test files against the unchanged frozen contract.

Attach must derive the expected claim order independently and pin `domain_hash_v1` for the production plan;
stored payload plus stored hash cannot define its own expected authority. Keep all generation-atomic source
fixes. Make the required concurrent test executable through the real batch-header path, deterministically
pause a bounded authentication page, bump the generation from the other public coordinator while that page
is active, and prove the same already-running public `run_until_idle` invocation receives/reopens on the
generation restart and completes the new boundary. Coordinate an actual public candidate commit after a
known auth page boundary, capture its domain, and assert that exact row is initially stale/current as
expected and is then authenticated without deletion or reacquisition. Preserve the exact per-candidate and
O(plans) state bounds, policy mismatch tests, forced page bound, and every earlier retained fix.

Sr does not run tests or migrations, edit other files or records, use RPC credentials, make network calls,
touch production data, or perform Git actions. Sr stops for fresh Sol source review with new hashes. Jr
integration/test execution and all controller/CLI, live readiness, RPC, staged production, coverage,
publication, downstream, PAPER, LIVE, and next-ticket work remain unauthorized. Next ticket remains
`NONE`.

## Sol eleventh source re-review - source fixes retained, test evidence rejected (2026-08-09)

Jr published the prior decision at commit `b34c893`; `HEAD` and `origin/main` both resolve to that commit.
Sol reviewed Sr's eleventh correction in the same six authorized files. The reviewed SHA-256 values are:

- `src/cryptofactors/acquisition/uniswap_v2_pair_events_v2.py`:
  `edc24e8b449aee96515d16455fbcbdb259231775ca621210a6560f8e14187a1c`;
- `src/cryptofactors/acquisition/uniswap_v2_pair_events_v2_engine.py`:
  `fc5ad160b88c2ef6f47100b60d1f607caadde528ecbdd8606513e28a05d1bbba`;
- `sql/migrations/0020_uniswap_v2_pair_event_v2_production_foundation.sql`:
  `f41175e3b23b24e8e5b5ba512a4fd10514201b1d156115664ff88f0442cb93bb`;
- `tests/acquisition/test_uniswap_v2_pair_events_v2.py`:
  `793fcf689aa32116db104cbd08566d79e9a104050f736fef808de336712e386c`;
- `tests/acquisition/test_uniswap_v2_pair_events_v2_engine.py`:
  `6fdcbf31a3d90fd650f2b5075d7602602fd510a8f1633ec2f7c6d41972ba8ca6`;
- `tests/acquisition/test_uniswap_v2_pair_events_v2_migration_0020.py`:
  `e77b2d08c10d96a475621ef9f161c8972b4bf78e6fbabb4854cb8d974cc94f67`.

The engine now takes expected claim order independently at attach, pins `domain_hash_v1` for the production
identity, retains complete plan/policy comparison before mutation, and preserves the generation-atomic page
and per-turn run-loop fixes. The test also installs the real batch-header fixture and attempts an exact
public candidate/generation proof. Those production-source fixes are retained; no further production source
or migration change is authorized by this review. The drop remains rejected before Jr integration because
the decisive test cannot reach its intended generation race:

1. The test monkeypatches `eng_a.coordinator._authenticate_candidate_row` globally and pauses on its first
   invocation. That method is used both by resume-page validation and by `commit_log_candidate` while the
   latter holds `BEGIN IMMEDIATE`. The setup makes this deterministic: A authenticates the first 32 of the
   33 initial candidates, then B's public `process_one` calls `claim_pending`, authenticates the remaining
   stale candidate, claims another node, and commits a new current-generation candidate. Consequently A's
   later `run_until_idle` has no stale candidate for its resume page; its first hooked authentication occurs
   when A commits another candidate inside the open write transaction.
2. The hook then waits on `mid_page_resume` while A holds SQLite's write lock. B observes the pause and calls
   `attach_existing_plan`, whose generation bump requires its own `BEGIN IMMEDIATE`; it blocks/fails with the
   database locked and cannot set the intended mid-page generation restart. The collected thread error is
   re-raised, so assertions for `generation_restart`, final safe-boundary completion, and the exact retained
   candidate are unreachable.

Targeted ruff, repository control, and `git diff --check` pass. Sol ran no pytest, migration, RPC,
production-data mutation, or Git operation.

## Authorized twelfth correction - engine test source only

Jr Dev - Hermes must first commit and push only this eleventh re-review in
`docs/handoff/CURRENT_TASK.md` and `tickets/DEX-003.md`, excluding the uncommitted six-file Sr drop,
`opencode.json`, and both untracked research files. After publication, Sr Dev - Grok Build may edit only
`tests/acquisition/test_uniswap_v2_pair_events_v2_engine.py`; the other five reviewed files are frozen at
the hashes above for this correction.

The test must pause specifically inside `_op_authenticate_resumed_candidates` after a successful raw replay
and before its generation-stamp transaction, without intercepting commit-time authentication or holding any
SQLite write transaction. Arrange at least one known stale candidate for that page, then bump through B's
public attach while A's single public `run_until_idle` remains active. Assert the returned restart page, the
same invocation's completion of the new generation, and the exact previously captured public candidate's
survival and final generation. Preserve the batch handler, independent policy/order rejection, 32+1 boundary,
and exact bounded-state assertions. Sr does not run tests, edit source/migration/other tests or records, use
RPC/network/production data, or perform Git actions; it stops for fresh Sol review. Jr integration/testing
and all controller/CLI, live readiness, RPC, staged production, coverage, publication, downstream, PAPER,
LIVE, and next-ticket work remain unauthorized. Next ticket remains `NONE`.

## Sol sixth source re-review - production foundation still rejected (2026-08-08)

Jr published the prior decision at commit `096f4cf`; `HEAD` and `origin/main` both resolve to that commit.
Sol reviewed Sr's sixth correction in the same six authorized files. The reviewed SHA-256 values are:

- `src/cryptofactors/acquisition/uniswap_v2_pair_events_v2.py`:
  `edc24e8b449aee96515d16455fbcbdb259231775ca621210a6560f8e14187a1c`;
- `src/cryptofactors/acquisition/uniswap_v2_pair_events_v2_engine.py`:
  `e7e31b7ec4200a0473b6dec904231b1ffac28e42d7803cbe221d02eed96c9040`;
- `sql/migrations/0020_uniswap_v2_pair_event_v2_production_foundation.sql`:
  `789288e94732a05a23fde41861313c23356eef6df1bb1d13385e22fc1686539f`;
- `tests/acquisition/test_uniswap_v2_pair_events_v2.py`:
  `793fcf689aa32116db104cbd08566d79e9a104050f736fef808de336712e386c`;
- `tests/acquisition/test_uniswap_v2_pair_events_v2_engine.py`:
  `c925ec7cd215a1d132257cd41da306fbf6ecf15fae64ce64c910641a1a7df6bb`;
- `tests/acquisition/test_uniswap_v2_pair_events_v2_migration_0020.py`:
  `5fd8f18f2161c2e5cf4d00c8a0a68b7c90308bf6eacb679304bc56600a42adea`.

The correction replaces the process-local backlog set with transactionally updated database rows plus an
O(1) counter, makes header store and candidate commit update them in the same transactions, and closes
the exact one-root metric assertions. Those fixes are retained. The drop remains rejected before Jr
integration for these blockers:

1. `candidate_auth` is lifetime state, not current-resume authentication. Candidate commit inserts a
   durable auth row that survives every engine restart. The resume query selects only candidates without
   that row, so an existing marked candidate is never raw-replayed before suppressing reacquisition in a
   new session. This violates the frozen requirement that all resumed candidate state/raw evidence
   authenticate before exclusion.
2. `force=True` resets only an in-memory cursor; it neither deletes/invalidates durable auth rows nor
   selects marked candidates. A candidate row or raw body tampered after commit remains trusted by claim
   exclusion. The existing `test_claim_fails_closed_on_tampered_candidate` commits a marked candidate,
   tampers its digest, then expects `force=True` to raise; the implementation examines zero candidates, so
   that senior test cannot pass.
3. The purported beyond-page test creates only two candidates, both within the 32-row page, manually
   deletes the later auth mark, and therefore does not exercise a candidate beyond the resume cursor. No
   test restarts a coordinator with more than one page of marked candidates, tampers a later raw/candidate,
   and proves it cannot suppress reacquisition.
4. Backlog bootstrap still contains the expressly prohibited one-time full population operation:
   `INSERT ... SELECT DISTINCT` scans all candidate-block rows and `COUNT(*)` scans all backlog rows under
   one `BEGIN IMMEDIATE`. Moving materialization from Python to SQLite fixes memory but not bounded work.
   Normal plan/migration initialization must establish coherent zero-state transactionally, and any repair
   path must be explicitly bounded/resumable rather than a full write-locked rebuild.

Targeted ruff, repository control, and `git diff --check` pass. Sol ran no pytest, migration, RPC,
production-data mutation, or Git operation.

## Authorized seventh correction - same six files only

Jr Dev - Hermes must first commit and push only this sixth re-review in
`docs/handoff/CURRENT_TASK.md` and `tickets/DEX-003.md`, excluding the uncommitted six-file Sr drop,
`opencode.json`, and both untracked research files. After publication, Sr Dev - Grok Build may correct
only the same six production-foundation source/test files against the unchanged frozen contract.

The correction must distinguish current-session resume validation from commit-time validation so every
pre-existing candidate is replayed before it can suppress reacquisition, in bounded pages, without
unbounded per-candidate memory; `force=True` must actually revalidate marked candidates. Add a true
beyond-page restart/tamper test. Remove the full backlog bootstrap transaction: initialize durable metric
state coherently when the plan/migration is created and use only bounded/resumable repair if missing or
inconsistent. Existing transactionally coherent backlog updates/counter, exact metrics, batch authority,
READY gate, indexed claim seek, keyset scheduling, immediate refill, and atomicity tests must remain.

Sr does not run tests or migrations, edit other files or records, use RPC credentials, make network calls,
touch production data, or perform Git actions. Sr stops for fresh Sol source review with new hashes. Jr
integration/test execution and all controller/CLI, live readiness, RPC, staged production, coverage,
publication, downstream, PAPER, LIVE, and next-ticket work remain unauthorized. Next ticket remains
`NONE`.

## Sol fifth source re-review - production foundation still rejected (2026-08-08)

Jr published the prior decision at commit `4aced85`; `HEAD` and `origin/main` both resolve to that commit.
Sol reviewed Sr's fifth correction in the same six authorized files. The reviewed SHA-256 values are:

- `src/cryptofactors/acquisition/uniswap_v2_pair_events_v2.py`:
  `edc24e8b449aee96515d16455fbcbdb259231775ca621210a6560f8e14187a1c`;
- `src/cryptofactors/acquisition/uniswap_v2_pair_events_v2_engine.py`:
  `bb3423ec5cb4e264e04a1717aa273d9097cd4c9a323d20b6a53f21992191864a`;
- `sql/migrations/0020_uniswap_v2_pair_event_v2_production_foundation.sql`:
  `aae2396957431419a7c72500d47f859b0c3a58e191e9bb6a137bc9690f6bc36d`;
- `tests/acquisition/test_uniswap_v2_pair_events_v2.py`:
  `793fcf689aa32116db104cbd08566d79e9a104050f736fef808de336712e386c`;
- `tests/acquisition/test_uniswap_v2_pair_events_v2_engine.py`:
  `7a0f15046b9701b1cd8c955794e212360c94976cc90948c95d9de9631898902d`;
- `tests/acquisition/test_uniswap_v2_pair_events_v2_migration_0020.py`:
  `5c10ed36fc2f572cd22f88074cc9e69c9411e20f83ef79695fa06fd3bf8ec540`.

The correction removes the per-claim count, makes resume replay keyset-paged, advances the missing-header
cursor, exercises semantic tamper through the READY method, calls the coordinator directly for the
candidate crash boundary, and distinguishes a one-slot refill from initial capacity. Those fixes are
retained. The drop remains rejected before Jr integration for these blockers:

1. Bounded resume authentication does not control candidate exclusion. `claim_pending` authenticates at
   most 32 candidates, then its `NOT EXISTS` predicate excludes every candidate row in the plan, including
   all rows beyond the authenticated cursor. A missing/raw-tampered 33rd candidate can therefore suppress
   reacquisition before it has authenticated. The source comment claiming exclusion applies only after
   replay is false; no authentication state participates in the SQL predicate.
2. Exact header backlog is implemented as a process-local `set[int]` containing every distinct missing
   block. Its first use performs a complete ordered distinct scan and materializes the full population.
   On resume, the first candidate commit can invoke that rebuild inside `BEGIN IMMEDIATE`; the first
   header scheduling turn can do the same. This restores unbounded memory and unbounded work precisely
   where the correction was required to remain bounded.
3. The process-local set cannot be an exact multi-process metric. A candidate committed by another engine
   process is not added to an already initialized set, and a header stored by another process is not
   removed. The set is also mutated during candidate transaction work without transactional rollback
   coupling. Exact backlog must derive from transactionally coherent repository state, not per-process
   mutable inventory.
4. No senior test places a tampered candidate beyond the resume page and proves it cannot suppress
   reacquisition. No test covers backlog population larger than the page, bounded-memory resume rebuild,
   or two-process candidate/header updates against exact backlog. The renamed exact-metrics test still
   uses `>=` for header members, in-flight high-water, and provider-attempt deltas even though its
   one-root fake-transport path has exact known values.

Targeted ruff, repository control, and `git diff --check` pass. Sol ran no pytest, migration, RPC,
production-data mutation, or Git operation.

## Authorized sixth correction - same six files only

Jr Dev - Hermes must first commit and push only this fifth re-review in
`docs/handoff/CURRENT_TASK.md` and `tickets/DEX-003.md`, excluding the uncommitted six-file Sr drop,
`opencode.json`, and both untracked research files. After publication, Sr Dev - Grok Build may correct
only the same six production-foundation source/test files against the unchanged frozen contract.

The correction must ensure only candidates authenticated for the current resume authority can suppress
reacquisition while keeping every claim/authentication turn bounded; replace the full in-memory backlog
set and one-time population scan with bounded, transactionally coherent, multi-process-safe exact backlog
state; and prove both properties with beyond-page tamper and cross-process backlog tests. The one-root
metric test must assert all exact known deltas. Existing batch replay, semantic READY gate, indexed claim
seek, header/finalization keyset cursors, immediate refill, coordinator crash-boundary, and forced
in-transaction finalization rollback must remain intact.

Sr does not run tests or migrations, edit other files or records, use RPC credentials, make network calls,
touch production data, or perform Git actions. Sr stops for fresh Sol source review with new hashes. Jr
integration/test execution and all controller/CLI, live readiness, RPC, staged production, coverage,
publication, downstream, PAPER, LIVE, and next-ticket work remain unauthorized. Next ticket remains
`NONE`.

## Sol fourth source re-review - production foundation still rejected (2026-08-08)

Jr published the prior decision at commit `db7bc62`; `HEAD` and `origin/main` both resolve to that commit.
Sol reviewed Sr's fourth correction in the same six authorized files. The reviewed SHA-256 values are:

- `src/cryptofactors/acquisition/uniswap_v2_pair_events_v2.py`:
  `edc24e8b449aee96515d16455fbcbdb259231775ca621210a6560f8e14187a1c`;
- `src/cryptofactors/acquisition/uniswap_v2_pair_events_v2_engine.py`:
  `025f3ef05f89627327001ed33cfd7600cea37213e2dd2fbc905db018d8b1c80b`;
- `sql/migrations/0020_uniswap_v2_pair_event_v2_production_foundation.sql`:
  `aae2396957431419a7c72500d47f859b0c3a58e191e9bb6a137bc9690f6bc36d`;
- `tests/acquisition/test_uniswap_v2_pair_events_v2.py`:
  `793fcf689aa32116db104cbd08566d79e9a104050f736fef808de336712e386c`;
- `tests/acquisition/test_uniswap_v2_pair_events_v2_engine.py`:
  `6ef9ff48e3eb39306ef42738bdd0ea0e9d5d48e12231510a8de026bfb0dd51da`;
- `tests/acquisition/test_uniswap_v2_pair_events_v2_migration_0020.py`:
  `5c10ed36fc2f572cd22f88074cc9e69c9411e20f83ef79695fa06fd3bf8ec540`.

The correction replaces claim-time candidate-prefix/N+1 walking with one indexed anti-candidate seek,
uses only an O(plans) session set, moves completed-slot refill before header work, keyset-pages
finalization discovery, and adds a valid forced failure after leaf/dependency writes. Those fixes are
retained. The drop remains rejected before Jr integration for these blockers:

1. Resume authentication is still an unbounded scheduling operation. The first `claim_pending` for a
   plan synchronously streams and fully raw-replays every stored candidate before it can claim one node.
   At production scale this can replay up to the full candidate population in one persistence command;
   every process repeats the full resume scan independently. It must be a bounded, resumable phase rather
   than one unbounded first-claim operation.
2. The alleged one-shot fast path still executes `SELECT COUNT(*)` across the plan's complete candidate
   table on every later claim even though the caller discards the count. Thus repeated claims retain
   population-sized database work despite removal of the N+1 prefix loop.
3. Missing-header discovery restarts at the beginning on every scheduling turn. Although its public API
   accepts `after_block_number`, the production loop never supplies or advances that keyset cursor. As
   acquired headers accumulate, `DISTINCT ... NOT EXISTS ... LIMIT` must repeatedly scan the growing
   already-covered prefix and can scan the whole candidate-block table when no missing block remains.
   Returned page size alone does not bound database work.
4. `header_backlog` is no longer the exact backlog required by the frozen contract. It is set to the
   length of a maximum-32 result page, explicitly saturating at 32 whenever more work exists. The test
   only asserts integer/nonnegative rather than the exact backlog.
5. The renamed `test_production_work_loop_exact_metrics` remains non-exact: it uses an `or`, lower bounds,
   a conditional assertion, and only `finalizations <= candidates`. It never pins the exact public-path
   deltas for claims, candidates, attempts, header backlog/batches/members/cache, or finalizations.
6. The new candidate crash test is not executable as written. Its trigger exception occurs inside
   `process_one`, whose broad exception handler converts it into an internal retry and returns a string;
   the test instead requires that `process_one` raise. The READY-root tamper test exercises a generic
   helper on a non-READY generic plan, not `authenticate_ready_root_manifest` on the resume gate. The
   refill test proves only the initial two-slot fill: two log calls before header work do not prove a
   completed slot was refilled, and its high-water assertion accepts one.

Targeted ruff, repository control, and `git diff --check` pass. Sol ran no pytest, migration, RPC,
production-data mutation, or Git operation.

## Authorized fifth correction - same six files only

Jr Dev - Hermes must first commit and push only this fourth re-review in
`docs/handoff/CURRENT_TASK.md` and `tickets/DEX-003.md`, excluding the uncommitted six-file Sr drop,
`opencode.json`, and both untracked research files. After publication, Sr Dev - Grok Build may correct
only the same six production-foundation source/test files against the unchanged frozen contract.

The correction must make resumed-candidate authentication bounded and resumable without allowing an
unauthenticated candidate to suppress reacquisition; remove every per-claim population scan; actually
advance bounded missing-header inventory without restarting through covered history; preserve an exact
header-backlog metric without a full scan per scheduling turn; and replace the remaining nominal tests
with decisive public-path assertions. The candidate crash test must observe the engine's real routed
outcome or invoke a public coordinator boundary that raises, READY tamper must exercise the READY resume
gate, refill ordering must distinguish a refill from initial capacity fill, and production metrics must
assert exact known deltas. Existing batch authority, semantic root replay, indexed claim seek, immediate
refill implementation, keyset finalization, and forced in-transaction finalization rollback must remain.

Sr does not run tests or migrations, edit other files or records, use RPC credentials, make network calls,
touch production data, or perform Git actions. Sr stops for fresh Sol source review with new hashes. Jr
integration/test execution and all controller/CLI, live readiness, RPC, staged production, coverage,
publication, downstream, PAPER, LIVE, and next-ticket work remain unauthorized. Next ticket remains
`NONE`.

## Sol third source re-review - production foundation still rejected (2026-08-08)

Jr published the prior decision at commit `9c7add1`; `HEAD` and `origin/main` both resolve to that commit.
Sol reviewed Sr's third correction in the same six authorized files. The reviewed SHA-256 values are:

- `src/cryptofactors/acquisition/uniswap_v2_pair_events_v2.py`:
  `edc24e8b449aee96515d16455fbcbdb259231775ca621210a6560f8e14187a1c`;
- `src/cryptofactors/acquisition/uniswap_v2_pair_events_v2_engine.py`:
  `9efa400b59f20dce4db8c10554a623d6572f7df56e7c24f35209e034f15ab815`;
- `sql/migrations/0020_uniswap_v2_pair_event_v2_production_foundation.sql`:
  `aae2396957431419a7c72500d47f859b0c3a58e191e9bb6a137bc9690f6bc36d`;
- `tests/acquisition/test_uniswap_v2_pair_events_v2.py`:
  `793fcf689aa32116db104cbd08566d79e9a104050f736fef808de336712e386c`;
- `tests/acquisition/test_uniswap_v2_pair_events_v2_engine.py`:
  `b6cd5bc8bad3f8b18e090b561a6e1540515af48795175c6ab9d06f8860cd4ccd`;
- `tests/acquisition/test_uniswap_v2_pair_events_v2_migration_0020.py`:
  `5c10ed36fc2f572cd22f88074cc9e69c9411e20f83ef79695fa06fd3bf8ec540`.

The correction makes canonical-header coordinator replay scalar-or-batch aware, reopens and hashes both
providers' retained evidence, recomputes every READY root identity from semantic fields, hard-bounds the
returned header/finalization pages, and adds useful batch/candidate tamper and exact batch-metric tests.
Those fixes are retained. The drop remains rejected before Jr integration for these blockers:

1. Claim selection remains production-quadratic. Every claim opens `BEGIN IMMEDIATE`, restarts at the
   first PENDING node, walks the entire candidate-backed prefix, and issues an additional candidate query
   for every row before reaching one claimable domain. The session set prevents repeated raw-file replay
   only after first authentication; it does not prevent the repeated prefix scan/N+1 SQL work under the
   write transaction, and the set itself grows without bound toward the full 1,858,348-root population.
2. Each header scheduling turn still performs two global `COUNT(DISTINCT block_number)` backlog scans.
   A scalar result does not make the database work bounded. `list_finalizable_candidates` can likewise
   inspect the complete candidate population when fewer than a page are ready. The correction therefore
   does not satisfy bounded work per scheduling turn even though returned lists are capped.
3. Immediate rolling replenishment is still absent. After `FIRST_COMPLETED`, `run_until_idle` consumes
   completed futures and then synchronously runs header acquisition/finalization before returning to the
   loop top that fills the newly open node slots. The smaller header page reduces the delay but does not
   preserve immediate logs-first capacity.
4. The required decisive senior tests remain incomplete. There is no READY root-row semantic-tamper
   resume test and no candidate-persistence crash-boundary test. The claimed atomic-finalization rollback
   test fails before entering the finalization transaction because headers are missing; it does not force
   a failure after leaf/dependency writes and prove transaction rollback. No test proves node-slot refill
   occurs before header work.
5. The production-loop metric test remains explicitly non-exact: it accepts claims *or* candidates,
   nonnegative backlog, and in-flight high-water *or* merely two provider attempts. The new exact batch
   metric test does not close the public production scheduling/aggregate metric contract.

Targeted ruff, repository control, and `git diff --check` pass. Sol ran no pytest, migration, RPC,
production-data mutation, or Git operation.

## Authorized fourth correction - same six files only

Jr Dev - Hermes must first commit and push only this third re-review in
`docs/handoff/CURRENT_TASK.md` and `tickets/DEX-003.md`, excluding the uncommitted six-file Sr drop,
`opencode.json`, and both untracked research files. After publication, Sr Dev - Grok Build may correct
only the same six production-foundation source/test files against the unchanged frozen contract.

The correction must remove the repeated candidate-prefix/N+1 claim path and unbounded session set while
authenticating all resumed candidates before they can suppress reacquisition; make every scheduling turn
bounded in database work as well as returned rows; refill completed node slots before any header turn;
and add decisive non-monkeypatched public-path tests for semantic READY-root tamper, candidate commit
crash boundaries, forced in-transaction finalization rollback, refill ordering, and exact production-loop
metrics. Existing scalar/batch replay, root semantic authentication, and bounded result-page fixes must
remain intact.

Sr does not run tests or migrations, edit other files or records, use RPC credentials, make network calls,
touch production data, or perform Git actions. Sr stops for fresh Sol source review with new hashes. Jr
integration/test execution and all controller/CLI, live readiness, RPC, staged production, coverage,
publication, downstream, PAPER, LIVE, and next-ticket work remain unauthorized. Next ticket remains
`NONE`.

## Sol source re-review - production foundation correction rejected (2026-08-08)

Jr published the first rejection at commit `11519b0`; `HEAD` and `origin/main` both resolve to that
commit. Sol reviewed the corrected uncommitted Sr Dev drop in the same six authorized files. The new
SHA-256 values are:

- `src/cryptofactors/acquisition/uniswap_v2_pair_events_v2.py`:
  `edc24e8b449aee96515d16455fbcbdb259231775ca621210a6560f8e14187a1c`;
- `src/cryptofactors/acquisition/uniswap_v2_pair_events_v2_engine.py`:
  `b685d125f4c4e17fa0707e6873513dda5cf01660174c1b540e12d129bbe4a342`;
- `sql/migrations/0020_uniswap_v2_pair_event_v2_production_foundation.sql`:
  `07d8c9661beb29943c7e7627b3430415b681ec8badfd74a4337ce1f445061a88`;
- `tests/acquisition/test_uniswap_v2_pair_events_v2.py`:
  `793fcf689aa32116db104cbd08566d79e9a104050f736fef808de336712e386c`;
- `tests/acquisition/test_uniswap_v2_pair_events_v2_engine.py`:
  `fb7956249ddc8554ff20684a1b39c5662b17fee5c5e285d47cdeca266d6639b4`;
- `tests/acquisition/test_uniswap_v2_pair_events_v2_migration_0020.py`:
  `2145b0dab5c044a968076b7463619c56f90cffcb8c927d326bbba4cbd7cb5158`.

The correction adds streamed external root hashing, READY re-authentication, candidate/raw replay,
batch parsing, scanner-over-cap coverage, and metric update sites. It remains rejected before Jr
integration for these blockers:

1. The public header-batch path cannot persist a batch request. `NetworkWorker.fetch()` accepts a JSON
   array, but `SpoolDescriptor.__post_init__` rejects every non-mapping request. Even if that validator
   were bypassed, `_op_persist_envelope` executes `dict(request)` and `request.get(...)`, which are invalid
   for the batch list. Both new batch tests therefore exercise a path that cannot reach batch parsing.
2. Batch-backed cached headers cannot replay through `acquire_header_batch`: its cache branch calls the
   scalar-only `_verify_cached_header`, which requires a mapping request/response and JSON-RPC object.
   Batch raw authority is an array and needs the batch-aware member authenticator already used later in
   finalization.
3. No global production header/finalization worker exists. `acquire_header_batch` and
   `finalize_candidate` have no production call sites; `run_until_idle` schedules only query-node work.
   Once log candidates exist, claim exclusion makes the node scheduler idle without enumerating distinct
   candidate blocks, batching missing headers, or finalizing ready candidates.
4. Claim exclusion still treats every candidate row as authenticated solely through SQL `NOT EXISTS`.
   It performs no resume replay before excluding the domain, so a tampered candidate/raw pair can suppress
   log reacquisition indefinitely. Authentication only occurs if a caller later invokes finalization.
5. Required senior evidence remains incomplete. The migration upgrade test claims every 0017-0019 table
   but populates only plan, node, lease, and execution policy; it omits coverage, chain identity, engine
   events, terminal receipts, raw rows, headers, leaves, and dependencies. Its query-plan assertion accepts
   any plan text containing `domain` or `using index` and never rejects `USE TEMP B-TREE`. Engine tests add
   only batch success and missing-member cases, not reorder/extra/duplicate/disagreement/tamper/shared-
   replay; candidate crash/tamper and atomic finalization public paths are also absent.
6. Exact metrics are not closed. Provider in-flight high-water is sampled immediately after future
   submission, before workers are guaranteed to acquire their limiters, so it can remain zero despite
   completed attempts. `header_backlog` is never measured or changed, and the batch/finalization metrics
   are not driven by an actual production work loop.

Targeted ruff, repository control, and `git diff --check` pass. Sol ran no pytest, migration, RPC,
production-data mutation, or Git operation.

## Authorized second correction - same six files only

Jr Dev - Hermes must first commit and push only this re-review in `docs/handoff/CURRENT_TASK.md` and
`tickets/DEX-003.md`, excluding the uncommitted six-file Sr drop, `opencode.json`, and both untracked
research files. After publication, Sr Dev - Grok Build may correct only the same six production-
foundation source/test files against the unchanged frozen contract. The correction must make batch
requests first-class through spool, persistence, recovery, authentication, and cached replay; add the
bounded global candidate-block/header/finalization work loop; authenticate candidates before claim
exclusion on resume; and replace the incomplete tests with decisive public-path coverage of every frozen
case, including exact query-plan and metrics assertions.

Sr does not run tests or migrations, edit other files or records, use RPC credentials, make network calls,
touch production data, or perform Git actions. Sr stops for fresh Sol source review with new hashes. Jr
integration/test execution and all controller/CLI, live readiness, RPC, staged production, coverage,
publication, downstream, PAPER, LIVE, and next-ticket work remain unauthorized. Next ticket remains
`NONE`.
