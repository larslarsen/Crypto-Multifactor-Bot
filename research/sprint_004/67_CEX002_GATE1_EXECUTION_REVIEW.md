# CEX-002 Gate 1 Execution Review

Date: 2026-08-18

Reviewer: Lead Quantitative Finance Researcher/Engineer

Decision: **REJECT REAL GATE 1 EXECUTION; DO NOT RERUN THE CURRENT IMPLEMENTATION**

## Reviewed state

- Published base: `origin/main == f1563cb475a7883be9f40ffb7669742f498f1bef`.
- Local accepted-source integration commit:
  `ddd6a59eda00c3f48019ef1f8a198992735f79d1`.
- Production source SHA-256:
  `4f60ef74478796acb138a34f55ba9f5f9808cbcaff83f0f09310a6cb4a9593a1`.
- CLI SHA-256:
  `af3aca3cf461ce2cfd31dd8db5b4aa53a9c1e5332a7bc8a622f250a3bb2855f6`.
- Test source SHA-256:
  `4ba04c535d81e9a6bac921b9b45844009f72694e48805fafd34a771a75e06abd`.
- Execution record SHA-256:
  `e148831066893e9b66c352c109d04c240e2fbe0e46e69c2828285310242a1fdc`.

The focused CEX-002 suite passed 29 tests, the directly depended-on atomic-download suite
passed 11 tests, and Ruff, repository control, and diff checks passed. The accepted source
integration is therefore publishable as a candidate. It is not an accepted Gate 1 data
result.

## Real-run result

The first authorized real qualification exited 1 while listing
`data/futures/um/monthly/trades/CELRUSDT/` after a transient Binance S3 connection reset.
The second run and semantic resume comparison correctly did not run under review 65.

The retained store contains approximately 691 MiB: 263 listing/checksum response blobs and
six checksum-verified raw sample objects. The six samples total approximately 685 MiB,
including one approximately 533 MiB monthly trades ZIP. The requested progress file does
not exist. All retained objects are evidence and must be preserved.

## Blocking findings

1. A transient connect/reset/timeout or retryable HTTP response can abort the entire
   qualification without bounded retry and durable incident evidence.
2. Listing responses are content-addressed, but there is no durable request identity that
   maps endpoint, prefix, delimiter, and continuation token to the retained response.
   Rerunning therefore repeats already completed remote traversal instead of proving reuse.
3. Sample progress is accumulated only in memory and written once after the entire
   qualification. An interruption after a verified object loses its object-to-digest,
   checksum, schema, and provenance checkpoint even though the bytes remain on disk.
4. The same physical archive families are traversed again for multiple logical products.
   This multiplies network work and failure exposure without adding source authority.
5. Sample selection is decided while traversing and downloads full monthly archives before
   a complete sample plan or byte budget exists. A qualification run downloaded hundreds
   of MiB for two early symbols before completing inventory, including a 533 MiB object.
   That is not operationally bounded source qualification.

These are real resumability and bounded-execution failures. Another run of the same source
would risk repeating hours of listing and large downloads, so it is expressly unauthorized.
This finding does not reject the source matrix semantics accepted in review 65.

## Publication transition

Jr Dev — Hermes must first publish the already-created candidate and this execution
evidence. It may stage only:

- `docs/handoff/CURRENT_TASK.md`;
- `research/sprint_004/65_CEX002_CLAUDE_SOURCE_REVIEW.md`;
- `research/sprint_004/66_CEX002_GATE1_EXECUTION.md`;
- `research/sprint_004/67_CEX002_GATE1_EXECUTION_REVIEW.md`; and
- `tickets/CEX-002.md`.

The local candidate commit already contains the reviewed source, tests, and fixtures; they
must not be rewritten or recommitted. Hermes runs only
`python3 scripts/check_repo_control.py` and `git diff --check`, verifies the staged path
list, commits the five records above, and pushes both local commits so
`HEAD == origin/main`. It preserves every unrelated dirty path and all of
`data/cex002_qualify`. It performs no network qualification or source edit.

Once the committed branch contains this review and the matching control-plane sections,
Sr Dev — Claude Build using Claude Opus 5 is automatically authorized for the correction
below. No ephemeral reviewer prompt or owner-supplied hashes are required.

## Bounded operational correction authorization

Claude may edit only:

- `src/cryptofactors/acquisition/binance_usdm_harmonic_qualification.py`;
- `scripts/research/qualify_binance_usdm_harmonic_sources.py`; and
- `tests/acquisition/test_binance_usdm_harmonic_qualification.py` plus the existing
  qualification fixture directory when a new deterministic fixture is necessary.

The correction must preserve the accepted source-authority semantics and close all five
findings above:

1. Inventory each unique physical family/prefix once, persist its complete pages, and
   derive every logical product matrix row from that shared inventory.
2. Persist an atomic request-keyed listing checkpoint containing the redacted endpoint,
   prefix, delimiter, continuation token, response digest/path, retrieval metadata, and
   parsed next-token identity. Rehash retained bytes before reuse. Bootstrap the existing
   263 content-addressed listing/checksum blobs where their request identity can be proven;
   otherwise retain them as unclaimed evidence rather than redownloading or misattributing
   them.
3. Atomically checkpoint each verified sample immediately after checksum, schema, and
   provenance validation. Recover the six existing raw samples by matching their retained
   provider-checksum/listing evidence and rehashing their bytes. Never redownload a proven
   retained sample.
4. Add bounded exponential-backoff retry with jitter control suitable for deterministic
   tests for connect/reset/timeout, HTTP 429, and HTTP 5xx failures across S3, FAPI,
   Coinalyze, checksum, and sample requests. Authentication, schema, checksum, and other
   terminal integrity failures fail immediately. Persist retry/incident counts without
   secrets.
5. Separate complete inventory from sample acquisition. Produce and persist a deterministic
   preflight sample plan before downloading any new sample. For Gate 1 qualification only,
   default to at most 256 MiB of new sample downloads in total and 64 MiB per new object;
   already retained verified objects do not consume this new-download budget. Choose the
   smallest adequate objects that preserve required headed/headerless schema and
   early/middle/recent/delisted regime evidence. If representative evidence cannot fit,
   emit a typed `sample_budget_exceeded` blocked result with the required object identity
   and size. Do not label the source inaccessible and do not omit its inventory.

The Gate 1 sample budget is an execution budget, not a source-size cap. It must not remove,
truncate, reject, or miscount larger source objects. Gate 2 remains responsible for full
accepted acquisition after Gate 1 review.

Tests must prove interruption and exact reuse at both layers: a reset during paginated
listing and an abort after a completed sample. On rerun, only uncompleted requests may be
fetched, retained bytes must be rehashed, the report's semantic identity must match an
uninterrupted run, and tampered checkpoints or bytes must fail closed.

Claude authors production and test source only. It performs no test execution, network
run, integration, repository-record edit, Git operation, commit, push, data deletion,
purchase, Gate 2 work, or model work. It stops for fresh reviewer source inspection with
exact hashes.

## Gate decision

Gate 1 remains `IN_PROGRESS`. Gate 2 and harmonic-model development remain unauthorized.
There is no partial PASS.
