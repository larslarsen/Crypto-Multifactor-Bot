# CEX-002 Gate-1 Acceptance and Storage-Sizing Architecture

**Date:** 2026-08-21  
**Reviewer:** Lead Quantitative Finance Researcher/Engineer  
**Decision:** Gate 1 `ACCEPTED`; bounded local storage-sizing source authorized  
**Gate 2:** Not accepted; bulk acquisition remains unauthorized

## Reviewed identity

The review covers commit `dea14dcd7606bd4fb01d035e7440d0b15f2b4abd` and these exact
artifacts:

- execution record 178;
- report 62: 13,559,766 bytes, SHA-256
  `bf01f88976e2ac3d224e843f340de726f5c8c337ba56a50f9e3c6f75c4d6f227`;
- manifest detail: 11,294,610 compressed bytes, SHA-256
  `576b3d7b03ff16fd492c5a9382e35f65e54d73ef3996c3a7fe5c6e6ba49b0fb4`,
  expanding to 466,713,055 bytes with SHA-256
  `1d21de4d68fb0dfd330dc480a0d27ddf2216c3b7d5e93b13ff70ea26230f968d`;
- live version-4 lock SHA-256
  `522271238e38a3652f9521b236981544782e02459450703f21e9ef344d476fa6`;
- post-qualification amendment-ledger SHA-256
  `259a1bfe274f402207dbd15e6e582fb4619bed62ddca5f606ea470755084b1b0`;
- accepted qualification production SHA-256
  `068763e2359abf4fc4fe4b7e7fdea95495db5c22bf362d468fec4056775ecb7e`;
- accepted qualification CLI SHA-256
  `473185ca946dcc37d506d8891e8f955708ff80c976a586967762c1294956d28f`.

`HEAD` and `origin/main` matched the reviewed commit. The reviewer used only read-only
Git, JSON, hash, manifest, archive-metadata, and filesystem-capacity inspection. The
reviewer did not run tests, acceptance commands, network commands, acquisition, or data
mutation.

## Gate-1 findings

Gate 1 is accepted. The corrected real-source run exited zero and reports
`gate_status=QUALIFIED`, `accepted=true`, no source-blocked product, 11 complete product
matrix rows, and no source incident. All nine source-gated products are qualified against
their declared official or secondary source; the two derived release products are
correctly excluded from source qualification.

The qualification retained 106 logical samples: 84 download rows, 12 retained rows, and
10 aliases. All 106 were reused, all checksums passed, every referenced object exists and
is non-empty, and no sample was newly acquired. Deduplication leaves 96 physical samples
across the 12 required Binance archive families and both headed and headerless forms.
The budget is settled at 84 charges and 1,049,324 charged/transferred bytes with zero
reservations and no breach.

Historical membership has 771 unique accepted perpetual identities, including 698
current perpetuals. Forty-six deliveries and 17 settlement aliases resolve without
authority mismatch; no historical member remains unresolved. Three current unarchived
contracts remain honest typed product gaps and do not masquerade as acquired coverage.

Coinalyze qualification uses real BTC/ETH liquidation, OI, funding, and price responses,
keeps the credential out of the query and evidence, and authenticates 569 supported
Binance perpetual mappings. The 202 unmapped contracts remain typed liquidation gaps.
The liquidation series remains explicitly observed/censored, not event-complete.

The seven `release_blocked_products` are expected full-coverage acquisition and
publication work: bars, taker flow, OI, realized funding, indicative funding, basis, and
cost calibration. They do not invalidate source qualification. They also do not pass any
later release gate.

## Storage finding

Report 62 proves these exact Binance compressed-raw components:

- selected archives: 7,833,966,625 bytes;
- complete bounded cost sample: 12,522,974,218 bytes in 3,144 objects;
- verified retained credit: 5,225,416 bytes in 73 objects;
- projected new Binance raw: 20,351,715,427 bytes;
- largest selected compressed object: 200,457,493 bytes.

The report correctly leaves total capacity unknown. The 20.35 GB value excludes the full
569-contract Coinalyze liquidation receipts, normalized and catalog outputs, immutable
publisher duplicate-stage high-water, and operating reserve. It must not be represented
as the complete release size.

Read-only inspection measured all 96 physical samples. Observed extracted-to-compressed
ratios vary materially by family, from roughly 2.42 through 14.22, which rejects a single
generic compression multiplier. The existing immutable publisher copies verified staged
output to a same-filesystem publication stage, so one largest-file allowance is also
insufficient. ADR-0021 therefore defines the required family-specific, real-sample,
lossless-envelope method and the full capacity equation.

## Accepted architecture

ADR-0021 is accepted and amends ADR-0017 storage preflight and ADR-0020 section 5. The
sizing implementation must be local, outcome-blind, pinned to the accepted Gate-1
authority, integer-only in projection arithmetic, and unable to change its cohort or
coefficients through CLI or library arguments.

The frozen Binance cohort is exactly the 96 unique physical retained samples selected by
the accepted 106-row plan. The implementation must derive it from accepted evidence,
deduplicate only proved aliases, require all 12 physical families, rehash every archive,
re-prove every provider checksum sidecar, inspect safe ZIP membership, and parse every
row under its declared schema. It must support the accepted headed/headerless forms and
must block on corruption, emptiness, path escape, unproved duplication, missing family,
unparseable data, or sample substitution.

Before measurement, the implementation must also re-prove the accepted qualification
production and CLI bytes and the report's version-4 plan, plan digest, code/config digest,
source-receipt, lock, ledger, manifest-detail, and source-identity bindings. A matching
report hash without its bound authority is insufficient.

The 12 exact physical families are:

1. daily `klines`;
2. daily `metrics`;
3. daily `premiumIndexKlines`;
4. daily `markPriceKlines`;
5. daily `indexPriceKlines`;
6. daily `bookTicker`;
7. daily `bookDepth`;
8. monthly `klines`;
9. monthly `fundingRate`;
10. monthly `premiumIndexKlines`;
11. monthly `markPriceKlines`;
12. monthly `indexPriceKlines`.

For each physical sample, the implementation must stream at most 65,536 rows per batch
into a lossless PyArrow/Zstandard Parquet envelope. One output row preserves every source
token plus physical family, venue symbol, economic interval, source key, and source-row
ordinal. Writer settings, column order, types, null representation, metadata, and row
group behavior must be deterministic. A whole extracted ZIP member may not be written to
disk or held in memory. An envelope record must expose compressed archive bytes,
extracted bytes, source rows, Arrow IPC bytes, Parquet bytes, footer/file overhead,
content hash, and writer identity.

For each family, the projection coefficient is the greatest observed exact rational
`parquet_bytes / compressed_archive_bytes`. Apply it with integer ceiling division to
every exact selected/cost compressed byte in that same family. Means, floating-point
arithmetic, fitted distributions, quantiles, manual padding, caller multipliers, and
cross-family substitution are prohibited. Fixed output multiplicities come only from
ADR-0021. The receipt must show every numerator, denominator, input byte count,
multiplicity, partition count, ceiling operation, and subtotal.

## Coinalyze projection contract

The implementation must rehash and parse the accepted future-market inventory and the
exact retained BTC/ETH daily liquidation, OI, funding, and price responses. It must prove
the accepted 569 supported mappings, preserve the 202 unmapped typed gaps, and reject a
supported mapping without authenticated lifecycle bounds through the qualification
cutoff. Typed unsupported mappings are not silently included or converted to zero.

For each retained response, calculate raw response framing bytes and exact point-token
bytes from the parsed response, then report point count, framing, and integer-ceiling
bytes per point. Use the greatest observed liquidation point charge and response framing
charge, one symbol per request, and each supported contract's authenticated lifecycle to
project the full raw liquidation receipts. Apply the same lossless deterministic-envelope
measurement to project normalized liquidation storage. OI, funding, and price remain
bounded reconciliation evidence and are not expanded into unrequested full panels.

No API key value may enter a URL, artifact, receipt, exception, or log. Sizing must need
no credential because it performs no network operation.

## Capacity and publication contract

Output partitioning is capped at one file per logical product, symbol, UTC month, and
source family. Catalog overhead is exactly 4,096 bytes per physical raw object, projected
normalized file, typed gap row, membership row, and Coinalyze receipt, plus the exact
report and compressed manifest-detail sizes. The implementation derives each count and
lists it in the receipt.

Temporary high-water is one full second normalized/catalog allocation plus the greater
of 200,457,493 bytes and the greatest projected normalized partition. Operating reserve
is `max(16 * 2^30, ceil(pre_write_available_bytes / 5))` and cannot be lowered by input or
rerun. The final future-storage requirement is the non-overlapping integer sum of new
Binance raw, new Coinalyze raw, normalized/catalog allocation, temporary high-water, and
reserve.

Sizing envelopes publish collision-safely under
`data/cex002_qualify/evidence/sizing/v1/envelopes/sha256/`. The versioned receipt target
is `research/sprint_004/180_CEX002_GATE2_STORAGE_SIZING.json`. The receipt reports
pre-write available bytes, post-publication available bytes, retained sizing-evidence
bytes, destination device identity, and the frozen reserve. Sufficiency compares the
future-storage requirement with post-publication available bytes, so retained evidence
is already charged and is not added twice.

The receipt must be canonical JSON and contain at least: schema/version and code identity;
all pinned input paths, sizes, hashes, and authority bindings; sorted blockers; sample and
alias accounting; per-family measurements and projections; Coinalyze mappings,
lifecycles, evidence, and projections; retained-credit proofs; raw/object/output/gap/
membership/receipt counts; partition and catalog calculations; largest partitions;
filesystem measurements; every capacity component; exact total; and
`storage_preflight_state` equal only to `sufficient` or `blocked`.

`sufficient` is not Gate-2 acceptance and cannot authorize acquisition. Any unknown,
missing, inconsistent, corrupt, unsupported, or non-integer component produces `blocked`
with an explicit stable reason. The CLI exits nonzero on invalid authority or failed
measurement; an honestly complete but capacity-insufficient receipt may publish with
`blocked` and a successful measurement exit.

Publication uses same-filesystem staging, fsync, collision comparison, atomic rename, and
cleanup. Failure cannot overwrite a nonidentical content-addressed artifact or the
versioned receipt. Existing exact evidence may be reused only after full revalidation.
The implementation may write only the sizing envelope tree and sizing receipt. It may not
call the network; mutate report 62, manifest detail, raw samples, lock, ledgers, plan,
checkpoint, caches, catalog, or control records; acquire data; normalize the release;
delete data; or accept a gate.

## Source authorization

Sr Dev - Claude Build using Claude Opus 5 is authorized to author exactly these new paths:

1. `src/cryptofactors/acquisition/binance_usdm_harmonic_sizing.py`
2. `scripts/research/size_binance_usdm_harmonic_release.py`
3. `tests/acquisition/test_binance_usdm_harmonic_sizing.py`

The production module owns typed local authority loading, verification, lossless-envelope
measurement, exact projection arithmetic, blocker semantics, and collision-safe evidence
publication. The CLI is a thin fixed-policy adapter with only path/destination arguments;
it exposes no cohort, family, coefficient, multiplicity, compression, batch-size,
overhead, credit, reserve, or capacity override. The test source must cover the complete
contract with deterministic synthetic ZIP/JSON/Parquet evidence and injected filesystem
measurements.

At minimum, tests must prove: exact authority acceptance; each pinned hash/size/binding
failure; gzip-detail corruption; archive/sidecar corruption; ZIP path escape and unsafe
membership; duplicate and alias disagreements; all 12 families; headed/headerless parsing;
empty/malformed/schema-invalid rows; 65,536-row batching; deterministic Parquet and JSON;
integer ceiling at boundaries larger than 2^53; fixed multiplicities and inability to
override them; per-family maximum selection; exact retained credit; catalog and partition
counts; immutable-publisher duplicate staging; largest-object versus largest-partition
selection; reserve rounding/floor/non-decrease; pre/post evidence capacity accounting;
Coinalyze framing, lifecycle, 569 supported mappings, 202 typed gaps, missing-lifecycle
block, credential absence/redaction, and no network; insufficient/unknown blockers; no
false Gate-2 acceptance; collision-safe reuse/rejection; path confinement; source-tree
immutability; and CLI exit semantics.

Claude runs no test, linter, control, Git, network, sizing, acquisition, or data command;
does not edit repository records or data; and does not modify any existing path. It returns
the three exact SHA-256 hashes and test-function count, then stops for reviewer inspection.

Hermes is not yet authorized. Gate 2, sizing execution, bulk acquisition, normalization,
catalog publication, NautilusTrader work, Harmonic Trader work, payoff analysis, PAPER,
LIVE, paid sources, reduced scope, and the next ticket remain unauthorized.
