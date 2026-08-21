# CEX-002 Listing Correction Source Review

Date: 2026-08-21

Reviewer: Lead Quantitative Finance Researcher/Engineer

Reviewed base: `2700e90a0b336543f29cf31d9570021407bf07ff`

Subject review: `research/sprint_004/117_CEX002_LISTING_SOURCE_REVIEW.md`

Reviewed source hashes:

| Path | SHA-256 |
|---|---|
| `src/cryptofactors/acquisition/binance_usdm_harmonic_qualification.py` | `b6077bf833ae59b2414b441564764179fc0dcff0db6cec3457139a5a26df53e8` |
| `scripts/research/qualify_binance_usdm_harmonic_sources.py` | `2288d32ed9f376bde62371d26dcf79b9a8597808d27bbc9a9a10148121b68009` |
| `src/source_audit/download.py` | `d658db5073a223eb5c5ded7b5c48b5e36c4078422cbdba38fd9ed031cbc0acd8` |
| `tests/acquisition/test_binance_usdm_harmonic_qualification.py` | `a45fdcb0fdbeb37da93c7020b8c594c404fddea6d115078c62659df714253ae0` |
| `tests/test_download_atomicity.py` | `2f181c33fbf0638cf7a67fa2292029c2c23db332527186dc1958d9661519e754` |

The CEX test source contains 183 uniquely named test functions. The atomic-download test
source contains 17 uniquely named test functions. The reviewer ran no test, Ruff,
repository-control, network, data, candidate, or migration command.

## Decision

**ACCEPT AND FREEZE THE MAIN QUALIFICATION MODULE. REJECT THE FOUR-PATH CLEANUP AND
PROOF RESIDUE BEFORE INTEGRATION.**

The correction closes the fresh-cache result shape, all seven stale accumulated test
contracts, concurrent pooled first use, synchronized checkpoint reuse/fetch counts,
post-success flush accounting, canonical report/journal retry ordering, and the serial
library default. The bounded inventory, checkpoint amortization, crash recovery,
known-bound skip, authority semantics, and data scope are accepted in the production
module at SHA-256 `b6077bf833ae59b2414b441564764179fc0dcff0db6cec3457139a5a26df53e8`.
That path is frozen.

Integration remains unauthorized because two new proof/cleanup defects remain.

## Findings

### 1. Serial-versus-bounded checkpoint proof reads files that cannot exist

`test_serial_and_bounded_listing_produce_identical_identity` invokes
`run_source_qualification` with `_trades_index`, which is a `MemoryObjectIndex`, and does
not pass a `ListingCheckpointStore`. The library does not create a listing checkpoint for
an arbitrary injected index. The test then reads
`<store>/cex002_listing_checkpoint.json` for both runs. Those files are never written, so
the new test necessarily fails with `FileNotFoundError` before proving request-to-content
mapping.

Keep the accepted semantic report comparison. Build the mapping proof with isolated
checkpoint-enabled `TransportObjectIndex` instances over deterministic scripted listing
responses, run the same inventory serially and bounded, flush both stores, normalize only
`retrieved_at` and local path roots, and compare canonical keys plus complete
request-to-content entries. Do not manufacture checkpoint documents in the test.

### 2. Cleanup and close evidence are still false on combined failure

The CLI uses:

```python
try:
    transport.close()
finally:
    listing_checkpoint.flush()
```

This guarantees both calls, but if both fail the later flush exception replaces the close
exception. The source comment and test claim the first failure remains primary, yet the
test injects only a close failure and a successful flush. Use explicit error capture so
both actions are attempted and the declared first cleanup failure is deterministically
re-raised; directly test both failures together. Preserve an already active body failure
under one documented rule rather than relying on implicit `finally` replacement.

`PooledHttpxTransport.close` increments `clients_closed` in `finally`, even when
`client.close()` raises. A failed close is therefore reported as a successful close and
the client reference is discarded. The counter must describe successful closure, and a
focused failing-client test must prove that the transport remains closed to new work,
reports no successful close, leaks no alternate client, and raises the close failure.

### 3. Retry-order test does not execute the concurrent path it claims to prove

`test_canonical_retry_evidence_survives_inverted_completion_order` manually constructs and
reverses incident dictionaries. It proves the sorting helper, but review 117 required
distinct retrying requests whose completion order is deliberately inverted. Add one
deterministic concurrent `RetryRunner`/journal test using distinct redacted labels and
controlled synchronization. Prove per-request attempt bounds, canonical final report
incidents, canonical durable journal incidents, and the same result under the opposite
completion schedule. No timing-only sleep assertion is acceptable.

## Claude residual authorization

Sr Dev - Claude Build using Claude Opus 5 is authorized to correct only:

- `scripts/research/qualify_binance_usdm_harmonic_sources.py`;
- `src/source_audit/download.py`;
- `tests/acquisition/test_binance_usdm_harmonic_qualification.py`; and
- `tests/test_download_atomicity.py`.

The accepted main qualification module and 17 fixtures are byte-frozen. Claude preserves
every accepted source/test direction and changes only cleanup error precedence, successful
close accounting, and the three direct proof contracts above. It must not weaken or remove
any accumulated test.

Claude performs no test, Ruff, repository-control, network/data run, candidate execution,
migration, integration, repository-record edit, ADR edit, Git operation, commit, push,
catalog work, Nautilus work, Harmonic Trader work, payoff analysis, PAPER, or LIVE work.
It stops for reviewer source inspection with exact hashes for the four authorized paths,
the frozen main-module hash, and both unique test-function counts. Hermes remains
unauthorized.

## Reviewer publication

The reviewer publishes exactly:

- `docs/handoff/CURRENT_TASK.md`;
- `research/sprint_004/118_CEX002_LISTING_CORRECTION_SOURCE_REVIEW.md`; and
- `tickets/CEX-002.md`.

No source/test path or unrelated dirty path belongs to the publication.

## Disposition

CEX-002 remains `IN_PROGRESS`. Gate 1 has not passed. Integration, tests, real candidate
execution, plan migration, sample acquisition, Gate 2, normalization, catalog publication,
Nautilus work, Harmonic Trader work, payoff analysis, PAPER, LIVE, and every other ticket
remain unauthorized. Next ticket remains `NONE`.
