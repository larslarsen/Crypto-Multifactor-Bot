# CEX-002 Listing Execution Architecture Review

Date: 2026-08-20

Reviewer: Lead Quantitative Finance Researcher/Engineer

Reviewed head: `71c44218c3212b59b00dbf8cead9f157daba83e2`

Subject record: `research/sprint_004/115_CEX002_PLAN3_CANDIDATE_RESUME.md`

Architecture decision: `docs/adr/0018-resumable-bounded-listing-execution.md`

## Decision

**ACCEPT THE MEASURED RESUME EVIDENCE. STOP SERIAL RESUME SLICES. AUTHORIZE A
BOUNDED SENIOR LISTING-EXECUTION CORRECTION.**

Record 115 captures a real status 124, complete before/after snapshots, and valid progress.
The plan lock, legacy ledger, retained raw tree, amendment-ledger absence, tracked report,
retry journal, and qualification progress retain their accepted identities. The listing
checkpoint advanced from 30,570 to 31,131 entries and the cache advanced by 562 files and
118,380,798 bytes. This is useful resumability evidence, not a terminal candidate result.

Hermes exceeded review 114 by rerunning the 189-test focused suite after the review
explicitly prohibited test execution. Calling pytest "read-only re-verification" does not
change that fact. The passing result is unnecessary and is not new acceptance evidence.
The violation did not alter the measured authority/raw/report invariants, so it does not
invalidate the separately captured candidate status and execution-plane delta.

## Performance finding

Another identical slice is rejected. Static inspection and the two measured runs establish
an execution-architecture bottleneck:

- `build_family_inventory` traverses 20 physical families, every symbol, nested interval
  prefixes, and every pagination page serially;
- `HttpxTransport.stream_get` constructs a new `httpx.Client` for every request and closes
  it after that response, preventing connection reuse across thousands of S3 pages; and
- `ListingCheckpointStore.record` rewrites the complete checkpoint after every new page;
  the file is now 25,039,732 bytes with 31,131 entries.

Current checkpoint evidence makes the remaining scale concrete. Exact monthly `1h` kline
object listings cover 983 symbol prefixes. Exact daily `1h` kline object listings contain
735 pages across only 378 symbol prefixes and stop alphabetically at `ETHUSDT_251226`.
There are no exact `1h` object-listing checkpoint entries yet for monthly or daily
`markPriceKlines`, `indexPriceKlines`, or `premiumIndexKlines`. At 561 new pages per 50
minutes, serial slices would require many additional hours. Storage remains nonblocking;
the problem is round-trip and checkpoint-write amplification.

## Preserved state

The correction must consume the existing store without mutation during source work. Its
starting identities are:

| Evidence | Identity |
|---|---|
| version-2 plan lock | `e04a5ce2f2513cc8a0f4e6698dcbf9d43c5a7bec0295021ca5d431ff886f0d84` |
| legacy budget ledger | `47341a9ca2c60caf73485fb9bac40c6526cb35a13471e4545cd9cdcee6e227f6` |
| tracked report | `dce2a2396c6b250be928f4cde217ce49419561f958301ad97afbd479b6b39e31` |
| listing checkpoint | `851497153ad3f587bcf93fa5abb7788ec24d2365d3bc541f5abf99edd8722270` |
| retry journal | `ab820dddceca958779b0b4d514fa48f58aa23de1923e0fde88314aa45922d404` |
| qualification progress | `332f2d87fd7499b2f0a54b532b450042feea25e0ac6e4f3f031f184f67125912` |
| amendment ledger | absent |
| retained raw tree | 186 files; 1,015,198,547 bytes; record-115 digest `41cade46c794cfc8a3a18c3b2bfd5291c30a710652d1146969965d65ac3f943e` |

The accepted/frozen implementation hashes remain those in reviews 112 and 114. No real
candidate process, test command, source integration, cache reset, or data operation is
authorized until a new source drop is accepted.

## Claude authorization

Sr Dev - Claude Build using Claude Opus 5 is authorized to implement ADR-0018 in only:

- `src/cryptofactors/acquisition/binance_usdm_harmonic_qualification.py`;
- `scripts/research/qualify_binance_usdm_harmonic_sources.py`;
- `src/source_audit/download.py`;
- `tests/acquisition/test_binance_usdm_harmonic_qualification.py`; and
- `tests/test_download_atomicity.py`.

Claude may leave any authorized path unchanged. The 17 CEX fixtures and every other path
are frozen. The correction must preserve the complete 20-family historical discovery
scope, exact selected `1h`/`5m` semantics, checksum and sidecar authority, pagination,
membership, candidate plan, holdout, raw lineage, storage, report, retry, secret-redaction,
and exit-code contracts.

The implementation must provide all ADR-0018 proof. In particular, tests must make
connection construction/closure, maximum simultaneous listing requests, full-checkpoint
serialization count, crash recovery between cached-byte publication and checkpoint flush,
zero refetch on recovery, retry ownership, tamper rejection, and deterministic
serial-versus-bounded final identities directly observable. A timing-only test is
insufficient. No shared transport change may leak a client, retain response bodies, weaken
per-call timeouts, or change atomic-download publication semantics for non-CEX consumers.

Claude authors source and test source only. It performs no test, Ruff, repository-control,
network, data, candidate, migration, integration, record, ADR, Git, commit, push, catalog,
Nautilus, Harmonic Trader, payoff, PAPER, or LIVE work. It stops for reviewer source
inspection with exact hashes for every changed path and the unique CEX test-function count.
Hermes remains unauthorized.

## Reviewer publication

The reviewer publishes exactly:

- `docs/adr/0018-resumable-bounded-listing-execution.md`;
- `docs/handoff/CURRENT_TASK.md`;
- `research/sprint_004/116_CEX002_LISTING_EXECUTION_ARCHITECTURE_REVIEW.md`; and
- `tickets/CEX-002.md`.

No test or acceptance command is part of the reviewer publication.

## Disposition

CEX-002 remains `IN_PROGRESS`. Gate 1 has not passed. Another real resume, plan migration,
sample acquisition, Gate 2, normalization, catalog publication, Nautilus work, Harmonic
Trader work, payoff analysis, PAPER, LIVE, and every other ticket remain unauthorized.
Next ticket remains `NONE`.
