# CEX-002 Claude Storage-Sizing Source Review

**Date:** 2026-08-22  
**Reviewer:** Lead Quantitative Finance Researcher/Engineer  
**Decision:** `REJECTED`; one bounded Sr Dev correction authorized  
**Gate 1:** Remains accepted  
**Gate 2:** Not accepted; sizing execution and bulk acquisition remain unauthorized

## Reviewed drop

The reviewer inspected Claude's three uncommitted, untracked paths at these identities:

| Path | SHA-256 |
|---|---|
| `src/cryptofactors/acquisition/binance_usdm_harmonic_sizing.py` | `9400e952a80db6bfe47cb5c46eb76cf07ca3714af048c888c7e46972bd9611c2` |
| `scripts/research/size_binance_usdm_harmonic_release.py` | `fba160fa5b4707d80cfde2d3fd16632cc0f2f1358f9b662ef73fba27c4603cb8` |
| `tests/acquisition/test_binance_usdm_harmonic_sizing.py` | `441b8a0ed6b7ae1f146bfc4a42893b16111909dc4f08761a8402331b6a767e3a` |

The test path contains 31 `def test_` functions. Scope is correct: Claude created only
the three review-179 paths and did not modify an existing repository path. The reviewer
performed static source/test inspection and read-only comparison with the accepted report,
lock, ledger, progress checkpoint, listing checkpoint, Coinalyze cache, and report-bound
evidence. The reviewer ran no test, linter, control, sizing, network, acquisition, or data
command.

## Findings

### 1. Critical - the accepted raw requirement is omitted and the real run stops

`family_input_bytes()` reads only acquisition manifest-detail rows and then requires all
12 sizing families (`binance_usdm_harmonic_sizing.py:1216-1245`). The accepted manifest
contains the 10 selected archive families, 733,203 objects, and 7,833,966,625 bytes. The
two cost families are deliberately a separate complete cost manifest in report
`storage.cost_sample`: 3,144 objects and 12,522,974,218 bytes.

Consequently, the real accepted input reaches the missing-family check with no
`daily/bookTicker` or `daily/bookDepth` row and cannot produce a receipt. If that check
were bypassed, `new_binance_raw = sum(totals) - retained_credit`
(`binance_usdm_harmonic_sizing.py:1341`) would omit the entire 12.523 GB cost component
and would subtract the 96-sample cohort bytes rather than the report's exact 73-object,
5,225,416-byte retained credit. It cannot re-prove the required 20,351,715,427 projected
new Binance raw bytes or the exact 736,347-object physical input.

### 2. Critical - caller-created Coinalyze authority can replace accepted evidence

The CLI requires an arbitrary lifecycle JSON and arbitrary Coinalyze directory, then
passes their content directly into sizing (`size_binance_usdm_harmonic_release.py:41-43,
64-76,90-94`). Production proves only that the caller supplies 569 lifecycle entries and
the integer 202 (`binance_usdm_harmonic_sizing.py:882-906`). It does not compare the
symbol sets, bounds, endpoint identities, response paths, sizes, or hashes to report 62.
A fabricated 569-symbol document therefore satisfies the count gate.

The accepted cache is content-addressed and has no `.json` suffix, so the CLI's
`glob("*.json")` finds zero real responses. If renamed copies were supplied, the same
loop would mix `/future-markets`, liquidation, OI, funding, and OHLCV documents even
though they have different schemas and roles. This violates the frozen-authority rule and
makes the real command unusable.

### 3. Critical - Coinalyze normalized storage is not measured

ADR-0021 requires a lossless deterministic liquidation envelope. The drop writes no
Coinalyze Parquet envelope. Instead it selects a Binance archive ratio with floating-point
division and applies that cross-family ratio to projected Coinalyze raw bytes
(`binance_usdm_harmonic_sizing.py:1308-1317`). This both violates the integer-only rule
and substitutes unrelated Binance CSV compression behavior for Coinalyze JSON/Parquet
behavior. The existing beyond-2^53 test exercises `ceil_div()` but never covers this
floating-point selection path.

### 4. Critical - partition and high-water calculations do not implement ADR-0021

The drop treats each raw object as a normalized output file and adds only one Coinalyze
file per supported symbol (`binance_usdm_harmonic_sizing.py:1319-1321`). ADR-0021 instead
requires grouping by logical product, symbol, UTC month, and source family. Daily objects
in the same month must group into one partition; a multi-year Coinalyze lifecycle requires
one partition per UTC month, not one lifetime file.

The largest partition is then calculated as family projected bytes divided by family
object count (`binance_usdm_harmonic_sizing.py:1334-1339`). That is an average object,
not the greatest projected symbol-month partition. It can understate the temporary
high-water component even when the family total happens to be conservative.

### 5. High - envelope measurements are not the claimed exact measurements

`extracted_bytes` is reconstructed from parsed token lengths plus one byte per cell
(`binance_usdm_harmonic_sizing.py:625-627`). It omits or alters quoting, delimiters,
line endings, BOMs, and headed-row bytes instead of reporting the ZIP member's exact
extracted byte count. `schema_kind` is always reported as `headerless` even for accepted
headed inputs (`binance_usdm_harmonic_sizing.py:613,651`). The checkpoint's accepted
headed/headerless identity is neither compared nor recorded.

`parquet_footer_overhead_bytes` is calculated as `parquet_bytes - Arrow IPC bytes`
(`binance_usdm_harmonic_sizing.py:645-657`). Arrow IPC is a different encoding and can be
larger than Parquet; their difference is not the Parquet footer or file overhead. The
accepted contract requires actual footer metadata measurement and a separately declared
file-overhead definition. Checkpoint status, recorded object byte size, checksum-match
state, schema kind/fields, and URL/key binding also need to re-prove before measurement.

### 6. High - receipt identity, rerun, and durable publication are inconsistent

The receipt includes a live `generated_at`, pre/post capacity, and first-run
published/reused counts, so an identical rerun produces different JSON and is rejected by
the immutable target (`binance_usdm_harmonic_sizing.py:1267,1373-1379`). The tests avoid
this by changing the receipt path on the second run. `receipt_sha256` is added to the
returned dictionary only after the earlier dictionary was serialized, so the returned
receipt and durable receipt are different objects (`binance_usdm_harmonic_sizing.py:1379`).
The constant string `SIZING_CODE_IDENTITY` is not the production/CLI byte identity required
by review 179.

Post-publication available bytes are measured before the receipt is published, not after
all retained sizing evidence. The caller can also select an arbitrary receipt path. File
renames are not followed by directory fsync, and the check-then-`replace()` sequence can
overwrite a concurrently created nonidentical destination. The optional
`frozen_reserve_bytes` library argument is itself a caller-selected reserve input, which
ADR-0021 prohibits even though the function only allows it to raise the number.

### 7. High - the tests certify synthetic shapes rather than the accepted contract

The synthetic fixture puts all 12 families into one manifest, supplies an invented
lifecycle map, and passes invented Coinalyze bytes directly to production. That hides the
accepted split between the 10-family manifest and two-family cost manifest, the
content-addressed report provenance, and real symbol/lifecycle authority.

The source guard at `test_binance_usdm_harmonic_sizing.py:881-884` forbids the substring
`requests`, while production itself emits a JSON field named `requests` at
`binance_usdm_harmonic_sizing.py:836`; the test source therefore contains a deterministic
failure before any architecture question. Missing coverage includes exact cost/listing
resolution, exact 20,351,715,427-byte reconciliation, Coinalyze provenance/symbol-set
substitution, lossless Coinalyze Parquet, real partition grouping, largest-partition
selection, exact extracted/footer measurements, complete durable-receipt equality,
directory durability/race behavior, and receipt-path confinement.

## Accepted correction contract

Gate 1 and ADR-0021 remain unchanged. Sr Dev - Claude Build using Claude Opus 5 is
authorized to correct only the same three untracked paths. Claude may rewrite them as
needed but may not broaden scope.

### Authority and exact physical inputs

1. Keep the exact report, manifest-detail, lock, amendment-ledger, qualification source,
   and qualification CLI pins from review 179.
2. Also pin and rehash the accepted qualification progress checkpoint at SHA-256
   `cc35a5c2c1fd72904d0d6a899565a763c89a38bb1295275e589e4d92be67eaff`,
   the accepted listing checkpoint at SHA-256
   `d584e22aaaa9414b06dbe13bc24dda0b01ed48e37bdf66f5b42f90865959bf9a`,
   and official contract metadata at SHA-256
   `e520f0f072730f566d027342ddc7e09f7b690ab80e76acbd40756759f13add1f`.
   Rehash every listing-cache response actually used to resolve cost-key sizes through
   its checkpoint-bound content address.
3. Stream and re-prove both compressed and uncompressed manifest-detail identities and
   record counts. Resolve the 10 archive families from its selected rows. Resolve all
   3,144 exact cost keys from report `storage.cost_sample.keys` through accepted listing
   evidence, including per-key positive integer size and family. Do not download or infer.
4. Reconcile exact totals before measurement: 733,203 selected archive objects and
   7,833,966,625 bytes; 3,144 cost objects and 12,522,974,218 bytes; 736,347 combined
   objects and 20,356,940,843 bytes; 73 rehashed/sidecar-proved retained objects and
   5,225,416 credit bytes; 20,351,715,427 projected new Binance bytes; no overlap and no
   unknown size.
5. Prove the plan action accounting `84 download + 12 reuse_retained + 10 alias = 106`
   and exactly 96 physical samples. Each alias must name an identical already selected
   physical key; action, family, symbol, interval, URL, size, checkpoint, schema, and
   sidecar evidence must agree.

### Coinalyze and lifecycle authority

1. Remove caller-supplied response bytes, evidence directories, lifecycles, typed-gap
   counts, cutoff, and normalized ratios from the production API and CLI.
2. Derive the exact five accepted provenance records from report `.coinalyze.provenance`;
   path-confine, size-check, and rehash each content-addressed cache body. Parse
   `/future-markets` as inventory, `/liquidation-history` as the only liquidation charge
   witness, and OI/funding/OHLCV only as retained overlap evidence.
3. Compare the complete ordered/sorted supported and unmapped symbol sets to report
   `.coinalyze.universe_support`, not merely their counts. Bind each supported mapping to
   the accepted future-market inventory and accepted Binance membership identity.
4. Derive lifecycle bounds from accepted report membership evidence and the pinned
   official metadata through the accepted qualification cutoff. Never accept a separate
   lifecycle file. A supported mapping without authenticated bounds yields an explicit
   stable blocked/unknown component; it never receives zero days or caller data.
5. Measure exact raw point/framing charges from the real retained liquidation response
   and produce real deterministic lossless BTC/ETH liquidation Parquet envelopes. Project
   normalized liquidation storage from the greatest exact Coinalyze envelope ratio using
   cross multiplication and integer ceiling only. Do not use any Binance family ratio or
   any floating-point comparison.
6. Report future-market inventory, bounded OI/funding/OHLCV evidence, projected liquidation
   receipts, exact retained credits, and projected new Coinalyze raw separately. Preserve
   one-symbol-per-request framing and observed/censored semantics.

### Measurement, partitions, capacity, and publication

1. Record exact ZIP member bytes, parsed rows, actual headed/headerless identity, Arrow
   IPC measurement, Parquet bytes, actual footer bytes, separately defined file overhead,
   writer settings, PyArrow version, and envelope hash. Stream source rows in batches no
   larger than 65,536 and reject unsafe membership, decoding/CSV errors, unexpected
   header form, width mismatch, empty data, or checkpoint disagreement with `SizingError`.
2. Use cross multiplication for every rational comparison. No `/` operation or float may
   participate in coefficient selection, byte projection, partition sizing, reserve, or
   sufficiency.
3. Build exact symbol/UTC-month/source-family groups from all selected and cost keys.
   Apply fixed logical multiplicity to group counts and group byte projections. Build
   Coinalyze symbol-month groups from authenticated lifecycles. The largest normalized
   partition is the maximum individual grouped projection, not a family average.
4. Derive every raw-object, normalized-file, typed-gap, membership-row, and Coinalyze-
   receipt count from accepted evidence and expose the source collection/count in the
   receipt. Reconcile all report summary totals.
5. Remove caller reserve input. Freeze reserve from pre-write available bytes; an exact
   prior receipt can only preserve a larger already-frozen value after its full identity
   re-proves. Account for the durable receipt itself before declaring post-publication
   capacity, without double counting retained evidence.
6. The CLI may accept only store/report/manifest/lock/checkpoint/listing/metadata path
   locations needed to find pinned bytes. The receipt destination is the fixed repository
   target from review 179; test-only APIs may inject a confined temporary repository root.
7. The canonical durable receipt and returned mapping must be identical. Do not add a
   self-hash field after publication. Report the sizing production and CLI SHA-256 bytes,
   deterministic policy identity, and separately return/print the receipt file hash.
   Rerun behavior must be explicit and tested without changing the target to evade a
   collision.
8. Use same-directory temporary files, streaming copies, file fsync, directory fsync,
   no-follow/path-confinement checks, and no-overwrite collision publication that cannot
   replace a racing nonidentical destination. Clean temporary files on every failure.

### Corrected tests and stop

Replace the synthetic all-12-family manifest with fixtures that reproduce the accepted
10-family manifest plus separate two-family cost/listing evidence and report-bound
Coinalyze provenance. Add every missing case above, including the real-shape exact-total
reconciliations, symbol-set substitution at unchanged counts, content-addressed files
without extensions, endpoint-role separation, Coinalyze envelope ratios beyond 2^53,
symbol-month partitions, largest grouped partition, headed/headerless checkpoint mismatch,
exact ZIP/footer accounting, full durable receipt equality, fixed-target rerun, directory
fsync/collision race, path escape, and no caller policy inputs. Fix the contradictory
network-source guard without forbidding harmless receipt field names.

Claude runs no test, linter, control, Git, network, sizing, acquisition, or data command;
does not edit records, data, or any path outside the exact three-path drop; returns the
three corrected SHA-256 hashes and test-function count; and stops for reviewer inspection.

Hermes remains unauthorized. No integration, sizing execution, Gate 2 acceptance, bulk
acquisition, normalization, catalog publication, NautilusTrader, Harmonic Trader, payoff,
PAPER, LIVE, paid source, reduced scope, or next-ticket work is authorized.
