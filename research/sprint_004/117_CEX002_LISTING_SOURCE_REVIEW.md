# CEX-002 Listing Execution Source Review

Date: 2026-08-21

Reviewer: Lead Quantitative Finance Researcher/Engineer

Reviewed base: `3bd988775bd54f90869b3631048902dc6b6dfbbd`

Subject architecture: `docs/adr/0018-resumable-bounded-listing-execution.md`

Reviewed source hashes:

| Path | SHA-256 |
|---|---|
| `src/cryptofactors/acquisition/binance_usdm_harmonic_qualification.py` | `3abd7ca42a33efcec4f09a6022a04fc98b0ca0d4ff96a0e7d8994a783097b110` |
| `scripts/research/qualify_binance_usdm_harmonic_sources.py` | `7cf00e0a0e4df00ddc315576599da3f5cfa3d870a7dfc5d627a8007a0d9af974` |
| `src/source_audit/download.py` | `d4399f7ec7ed6c74b2062d796b5484aef3aba4b20cc23125df45c9eaf38c0245` |
| `tests/acquisition/test_binance_usdm_harmonic_qualification.py` | `b7b5f817e2b75576ebdcbc0e1acb82133262f588b540ddc3470333a09542027b` |
| `tests/test_download_atomicity.py` | `0d543a1307e8636476c5cef051220c4d29a1420d478db143a0adc43db17f6306` |

The CEX test source contains 176 uniquely named test functions. The atomic-download test
source contains 16 uniquely named test functions. The reviewer ran no test, Ruff,
repository-control, network, data, candidate, or migration command.

## Decision

**REJECT BEFORE INTEGRATION. PRESERVE THE EXECUTION ARCHITECTURE; CORRECT THE COLD
PATH, TEST CONTRACTS, AND CONCURRENT STATE.**

The drop takes the right architectural direction: a bounded reusable transport, at most
eight workers, submission-window backpressure, input-order inventory consumption,
single-lock checkpoint serialization, 256-page amortization, explicit normal-boundary
flush, content-addressed crash recovery, and known-bound bootstrap skipping. The complete
20-family data scope and all financial/source-authority semantics remain intact.

Integration and real execution remain unauthorized because the implementation and its
proof are incomplete.

## Findings

### 1. Fresh-store CLI fails before its first listing

`ListingCheckpointStore.bootstrap` returns only `claimed`, `checksum_blobs`, and
`unclaimed` when `list_cache` does not yet exist. The CLI unconditionally reads
`bootstrapped["skipped_already_bound"]`. A legitimate fresh store therefore raises
`KeyError` before the first remote listing. The bootstrap result must have one stable
shape on every branch, and a focused CLI test must exercise an absent cache directory.

### 2. The accumulated suite is statically inconsistent with amortized durability

At least seven pre-existing tests cannot satisfy their current assertions:

- `test_listing_checkpoint_reuses_completed_pages_after_a_reset` reloads an unflushed
  checkpoint instead of recovering the retained page through bootstrap;
- `test_listing_checkpoint_rehashes_and_fails_closed_on_tampered_bytes` reloads before an
  explicit flush, so it no longer loads the entry it intends to tamper-check;
- the four tests using `_listing_store_with_two_prefixes` read a checkpoint path that the
  helper no longer causes to be written; and
- `test_cli_noncandidate_initialization_is_unchanged` still searches the AST for
  `HttpxTransport`, although the executable now constructs `PooledHttpxTransport`.

The tests must be updated to express ADR-0018, not weakened. Bound-entry tamper rejection,
unflushed-byte recovery, zero refetch, canonical request keys, cache-local paths,
pagination binding, and preflight ordering all remain mandatory.

### 3. Shared concurrent state is not fully synchronized

`PooledHttpxTransport._ensure_client` has no lock. Concurrent first use can construct
multiple clients, overwrite the retained client reference, leak the losers, and exceed the
declared pool lifecycle evidence. `requests_sent`, construction/closure counters, and
close-versus-create state are also unsynchronized. The CLI currently performs a serial root
request before symbol workers, which masks first-use races in that one call path; the
shared transport contract and its tests cannot rely on that accident.

`ListingCheckpointStore.record` serializes writes, but `retained_bytes` reads shared
entries and increments `reused` outside the lock, while `TransportObjectIndex._list_page`
increments `fetched` outside the store lock. Counts may be lost and execution evidence may
be inaccurate. All shared mutation and the minimum entry snapshot needed for concurrent
reuse must have an explicit synchronization contract without holding a lock during file
hashing or XML parsing.

### 4. Failed checkpoint writes publish false in-memory state

`ListingCheckpointStore._flush` increments `serializations` and clears
`pending_records` before `_atomic_write_json` succeeds. If that write fails, the caller
sees a serialization that did not occur and the final explicit `flush()` becomes a no-op.
Content-addressed cache recovery protects the next process, but current-process evidence
is false and the write is not retried. Commit counters and pending-state changes only after
successful atomic publication; test the failure path.

### 5. Retry and cleanup proof remains incomplete

Concurrent calls append retry incidents and durable journal rows in completion order. The
current test proves only aggregate attempt counts for four identical labels; it does not
prove deterministic evidence order when distinct requests fail in deliberately inverted
completion order. Canonical final report/journal ordering must be explicit and tested.

The CLI cleanup also calls `transport.close()` before `listing_checkpoint.flush()` in one
`finally` suite. If close raises, the checkpoint flush is skipped. Both cleanup actions
must be attempted under nested cleanup, with deterministic primary-error behavior and
focused injected-failure proof.

### 6. Concurrency became an implicit library default

`run_source_qualification` now defaults to eight workers. That silently changes every
programmatic caller and makes existing fixture/mocked indexes concurrent without an
explicit request. Per the ADR-0018 clarification, the library default remains one; the
production CLI passes its bounded default explicitly. The serial-versus-bounded proof must
compare semantic report identity and normalized request-to-content bindings, not raw
checkpoint SHA across independent retrieval timestamps.

## Reviewer architecture clarification

Review 116 required a stable "final checkpoint identity" across independent serial and
bounded cold runs. That wording was overstrong because the checkpoint intentionally keeps
real per-response retrieval timestamps, which legitimately differ. The reviewer has
amended ADR-0018 in this publication: scheduling may not change request-to-content
bindings, canonical key order, semantic report identity, or incident order; tests compare
checkpoint mappings after normalizing only real retrieval timestamps. No source or data
scope is changed by this clarification.

Controlled Python exception/cancellation paths must close pooled resources. Abrupt process
termination relies on OS cleanup plus retained-byte bootstrap recovery; no implementation
can promise Python `finally` execution after an uncatchable kill.

## Claude corrective authorization

Sr Dev - Claude Build using Claude Opus 5 is authorized to correct the rejected drop in
the same five paths and no others:

- `src/cryptofactors/acquisition/binance_usdm_harmonic_qualification.py`;
- `scripts/research/qualify_binance_usdm_harmonic_sources.py`;
- `src/source_audit/download.py`;
- `tests/acquisition/test_binance_usdm_harmonic_qualification.py`; and
- `tests/test_download_atomicity.py`.

Claude preserves the accepted connection-pool, bounded-worker, backpressure,
input-order-consumption, amortized-checkpoint, retained-byte-recovery, and known-bound-skip
direction. It closes every finding above and adds direct deterministic proof for the cold
cache path, concurrent first client construction, exact worker ceiling, synchronized
checkpoint counters, successful-versus-failed flush state, both cleanup attempts,
inverted-order distinct retry failures, normalized serial-versus-bounded checkpoint
mapping, zero-refetch recovery, and all retained tamper/identity contracts.

The 17 fixtures and every other path remain frozen. Claude performs no test, Ruff,
repository-control, network/data run, candidate execution, migration, integration,
repository-record edit, ADR edit, Git operation, commit, push, catalog work, Nautilus work,
Harmonic Trader work, payoff analysis, PAPER, or LIVE work. It stops for reviewer source
inspection with exact changed-path hashes and both unique test-function counts. Hermes
remains unauthorized.

## Reviewer publication

The reviewer publishes exactly:

- `docs/adr/0018-resumable-bounded-listing-execution.md`;
- `docs/handoff/CURRENT_TASK.md`;
- `research/sprint_004/117_CEX002_LISTING_SOURCE_REVIEW.md`; and
- `tickets/CEX-002.md`.

No rejected source/test path or unrelated dirty path belongs to the publication.

## Disposition

CEX-002 remains `IN_PROGRESS`. Gate 1 has not passed. Integration, tests, real candidate
execution, plan migration, sample acquisition, Gate 2, normalization, catalog publication,
Nautilus work, Harmonic Trader work, payoff analysis, PAPER, LIVE, and every other ticket
remain unauthorized. Next ticket remains `NONE`.
