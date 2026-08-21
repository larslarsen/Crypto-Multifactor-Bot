# CEX-002 Grok Report Split Residual Review

Date: 2026-08-21

Reviewer: Lead Quantitative Finance Researcher/Engineer

Reviewed base: `3ea5c69ab7b56ed75dc430342c36df523ff0cb6a`

Governing authority: `research/sprint_004/124_CEX002_GROK_REPORT_SPLIT_CONTINUATION.md`

Reviewed hashes:

| Path | SHA-256 |
|---|---|
| `src/cryptofactors/acquisition/binance_usdm_harmonic_qualification.py` | `d6d89ef1acc8401de54f17906f8b689c2cedad9b67910f0c5c9f361c34cebd23` |
| `scripts/research/qualify_binance_usdm_harmonic_sources.py` | `b4e9235406be5276619b4a69017ddb87a8cffefb691c2673f2e3b875cc775d96` |
| `tests/acquisition/test_binance_usdm_harmonic_qualification.py` | `3c57e61c840b94acba4a4e7af1130205482698aabb2475244fc9015c105130f3` |

The CEX test source contains 207 uniquely named test functions. The preserved oversized
report remains exactly 1,059,297,547 bytes at SHA-256
`46d1980ecf384874e45c4c31f142c16efc5472ef63231e9456e264f3e94ef691`.
The reviewer performed source inspection and a whitespace-error inspection of the three
authorized paths. No pytest, Ruff, repository-control, network, data, candidate, plan
migration, or acceptance command was run.

## Decision

**REJECT BEFORE HERMES INTEGRATION. ONE EXPLICIT ADR-0019 BOUNDED-MEMORY REQUIREMENT
REMAINS OPEN.**

Grok completed the prevalidation, compressed and uncompressed identity, strict relative
content address, canonical JSONL, row-derived aggregates, family totals, pending-sequence
reconciliation, record order, collision-safe temporary publication, fsync, injected
partial-write/replace proofs, bounded writer, and effective no-duplication assertions.
Those corrections are accepted direction and must be preserved.

## Blocking finding

### The validator retains the entire row-key population

`validate_manifest_detail` declares that its pass is bounded, but initializes
`row_keys: set[str]` and inserts every selected key. The completed real manifest has
733,203 rows, so validator auxiliary memory grows linearly with the evidence it is meant
to stream. This directly leaves review 123 finding 3's requirement to reconcile order and
duplicate keys "without unbounded memory" open. It also leaves review 124's bounded
recomputation requirement open.

The added boundedness proof covers `manifest_detail_records` and `_write_detail_stream`
only. It neither inspects nor exercises the validator's whole-key accumulator. Therefore
the test suite would certify the writer while missing the remaining production defect.

## Surgical correction authority

Sr Dev - Grok Build using Grok 4.6 High is authorized to correct only:

- `src/cryptofactors/acquisition/binance_usdm_harmonic_qualification.py`; and
- `tests/acquisition/test_binance_usdm_harmonic_qualification.py`.

The CLI is accepted and frozen at
`b4e9235406be5276619b4a69017ddb87a8cffefb691c2673f2e3b875cc775d96`.

At the existing manifest-construction boundary, establish deterministic canonical row
order with `key` as the primary identity component. Derive the pending-key sequence from
that same order. In the validator, enforce the identical key-primary strict order and
reject a repeated key using only the immediately prior key/identity; remove `row_keys` and
every other row-population-sized accumulator. Preserve constant-memory rolling pending
digests and fixed-family aggregate state.

Add focused test source that:

- proves a duplicate key with otherwise changed row fields still fails closed under the
  key-primary contract;
- proves noncanonical row order still fails closed;
- proves detail round-trip and pending order use the new canonical row order; and
- directly proves the validator contains no whole-row/key collection accumulator or
  collection-sized sort/copy.

Do not weaken duplicate detection to full-tuple uniqueness: `key` is the selected physical
object identity. Do not add a Bloom filter, approximate check, external database,
dependency, second key-index phase, row duplication, or another full collection. Preserve
every accepted prevalidation, descriptor/header, aggregate, canonical encoding/path,
atomicity, receipt, content-address, universe, selected-row, financial-semantics, plan,
budget, retry, checkpoint, secret, no-download, and exit-status contract.

Grok performs no test, Ruff, repository-control, network/data run, candidate execution,
integration, record or ADR edit, Git operation, commit, push, plan migration, sample
acquisition, Gate 2, catalog, Nautilus, Harmonic Trader, payoff, PAPER, LIVE, or
other-ticket work. It stops for reviewer source inspection with exact hashes for the two
authorized paths, the frozen CLI hash, and the unique CEX test-function count. Hermes
remains unauthorized.

## Reviewer publication

The reviewer publishes exactly:

- `docs/handoff/CURRENT_TASK.md`;
- `research/sprint_004/125_CEX002_GROK_REPORT_SPLIT_RESIDUAL_REVIEW.md`; and
- `tickets/CEX-002.md`.

No source/test path, oversized report, data, checkpoint, cache, journal, database sidecar,
or unrelated dirty path belongs to this publication.

## Disposition

CEX-002 remains `IN_PROGRESS`. Gate 1 has not passed. Integration, report rerun, plan
migration, sample acquisition, Gate 2, normalization, catalog publication, Nautilus work,
Harmonic Trader work, payoff analysis, PAPER, LIVE, and every other ticket remain
unauthorized. Next ticket remains `NONE`.
