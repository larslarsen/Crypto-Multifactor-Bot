# CEX-002 Claude Storage-Sizing Correction Review

**Date:** 2026-08-22  
**Reviewer:** Lead Quantitative Finance Researcher/Engineer  
**Decision:** `REJECTED`; one final bounded Sr Dev correction authorized  
**Gate 1:** Remains accepted  
**Gate 2:** Not accepted; sizing execution and bulk acquisition remain unauthorized

## Reviewed drop

The reviewer inspected Claude's corrected three-path, uncommitted source drop at these
identities:

| Path | SHA-256 |
|---|---|
| `src/cryptofactors/acquisition/binance_usdm_harmonic_sizing.py` | `c8da722a2f45d288142312acc62617e5160b5ce0abae2d83f1d4f1dd113b9da5` |
| `scripts/research/size_binance_usdm_harmonic_release.py` | `5cc8117563d0d07e369e75bfacae08c7c76123477ee7bfdb19264a61a8464658` |
| `tests/acquisition/test_binance_usdm_harmonic_sizing.py` | `b634bcaf3afd1323bc1cf7cf17de9c414ba6700150c1ee39780193b9040882f6` |

The test path contains 29 `def test_` functions. Scope remains correct: no existing path
was edited. The reviewer performed static source/test inspection and read-only comparison
with report 62 and ADR-0021. The reviewer ran no test, linter, control, sizing, network,
acquisition, or data-mutation command.

The correction closes the first review's separate cost-manifest resolution,
report-bound Coinalyze provenance, exact-rational Coinalyze envelope, symbol-month
grouping, fixed CLI target, and basic collision-publication defects. It is not safe for
Hermes integration because the real run still cannot complete and several capacity and
publication invariants remain false.

## Findings

### 1. Critical - retained acquisition credit is still replaced by the 96-sample cohort

`run_storage_sizing()` increments `credit_objects` and `credit_bytes` for every one of the
96 sizing samples, then passes those values to `reconcile_physical_inputs()`
(`binance_usdm_harmonic_sizing.py:2018-2068`). The accepted report proves a different set:
73 consumable acquisition-manifest objects and 5,225,416 verified bytes. The 96 sizing
samples total 1,093,966 bytes: 1,049,324 downloaded plus 44,642 retained sample bytes.

The real run therefore supplies `96 / 1,093,966` where reconciliation requires
`73 / 5,225,416` and raises before publishing the receipt. It has already durably
published sizing envelopes at that point. The synthetic fixture hides the defect by
setting `ACCEPTED_RETAINED_CREDIT_OBJECTS = len(cohort_rows)` and its bytes to those same
cohort archives (`test_binance_usdm_harmonic_sizing.py:405-413`).

The correction must derive the 73-object credit from the accepted manifest's consumable
rows, join each exact key to the pinned progress/checksum authority, rehash the object and
sidecar, prove 5,225,416 bytes, and keep that proof separate from the 96 coefficient
samples. All failure-prone reconciliation must precede durable publication.

### 2. Critical - projected new Coinalyze raw and receipt counts are not the required set

`project_coinalyze()` returns only a gross liquidation projection
(`binance_usdm_harmonic_sizing.py:1790-1828`). The capacity component labels that gross
value `new_coinalyze_raw_bytes` without separately counting the future-market inventory
receipt or proving and subtracting exact reusable acquisition coverage
(`binance_usdm_harmonic_sizing.py:2103-2105`). Report 62 retains a 1,449,633-byte market
inventory response and a 40,826-byte two-symbol liquidation response; their roles and
economic coverage cannot disappear or be credited by a bare byte subtraction.

Catalog overhead separately sets `coinalyze_receipts` to the five qualification
provenance records (`binance_usdm_harmonic_sizing.py:2078-2088,2173-2187`). Those five
records are bounded sizing/reconciliation evidence, not the projected 569 one-symbol
liquidation acquisition receipts plus the inventory receipt required by ADR-0021.

The correction must expose gross required Coinalyze raw, exact retained receipts/bytes and
coverage, projected new raw, inventory receipts, liquidation receipts, and bounded
overlap-evidence receipts as distinct non-overlapping fields. Derive the catalog receipt
count from the projected acquisition receipt set. Reconcile the equation in tests using
the real accepted response shape, including the retained two-symbol request versus the
one-symbol projection rule.

### 3. Critical - the fixed receipt is neither exactly accounted nor reproducible

The claimed receipt size is measured from a different skeleton which omits the populated
filesystem, state, authorization, and real blockers
(`binance_usdm_harmonic_sizing.py:2203-2228`). The reported durable receipt bytes and the
post-publication capacity subtraction therefore do not describe the published receipt.

An identical fixed-target rerun also cannot produce the same document. The first run
reports newly published envelopes and pre-write space before those envelopes; the next
run reports reused envelopes and a different pre-write state
(`binance_usdm_harmonic_sizing.py:2016,2047-2061,2179-2180`). A normal CLI rerun also gets
a new `generated_at`. This contradicts the asserted equality in
`test_rerun_at_the_same_fixed_target_is_explicit()` before Hermes runs it. Finally,
`preserved_reserve_bytes()` trusts any existing mapping with only matching schema and
policy strings rather than re-proving the complete prior receipt identity
(`binance_usdm_harmonic_sizing.py:1886-1903`).

The correction must make first publication account for the exact final canonical receipt
length and compare sufficiency with space after evidence plus that exact receipt. Define
rerun semantics which fully revalidate and return the identical durable fixed-target
receipt without outcome-dependent counters or timestamps changing it. A prior receipt may
preserve a reserve only after its complete authority, code, evidence, filesystem, capacity,
and canonical-byte identity re-prove. Add a test which would fail when published/reused or
available-space observations change on the second invocation.

### 4. High - largest partition combines multiple logical files

For every family group, `project_families()` multiplies one partition projection by output
multiplicity before selecting `largest_partition_bytes`
(`binance_usdm_harmonic_sizing.py:1304-1323`). A kline group produces two separate logical
files, not one file twice as large. ADR-0021 and review 181 require the largest individual
projected partition. The test at lines 800-804 enshrines the combined value.

Keep the multiplicity in family total and partition count, but select high-water from one
logical file's projected bytes. Correct the focused assertion and cover multiplicity one
and greater than one.

### 5. High - the integer-only guard deterministically rejects the source

`_utc_day_from_ms()` uses `int(value) / 1000`
(`binance_usdm_harmonic_sizing.py:1605-1606`). The test at lines 732-737 scans production
source and rejects a non-string `" / "`, so the submitted source contradicts its own test.
Use integer epoch conversion with `// 1000` and keep all lifecycle/projection arithmetic
integer-only.

### 6. High - publication still lacks the required streaming and no-follow guarantees

Envelope publication loads the complete Parquet source with `source.read_bytes()` and
hands it to a whole-payload writer (`binance_usdm_harmonic_sizing.py:1914-1969`), contrary
to review 181's streaming-copy requirement. Existing targets are inspected through
`is_file()`, `read_bytes()`, and ordinary opens; a same-root symlink can therefore be
followed. Receipt publication has no independent target confinement/no-follow proof. The
test source contains no symlink/no-follow or directory-fsync case.

Stream-copy envelope files through a same-directory temporary file while hashing, fsync
the file and directory, reject every symlink component/target with no-follow checks, and
publish no-overwrite under races. Apply equivalent confinement/no-follow behavior to the
fixed receipt. Test symlink target and parent rejection, directory fsync, collision races,
full cleanup, and bounded reads.

## Decision and exact correction boundary

The corrected drop is rejected. Gate 1 remains accepted; Gate 2 and Hermes integration
remain unauthorized. Sr Dev - Claude Build using Claude Opus 5 is authorized for one
final surgical correction of only the same three untracked paths. Preserve every accepted
review-181 correction and close only the six findings above.

The corrected tests must stop redefining acquisition credit as the sizing cohort and must
exercise a fixture with separate 73-like consumable credit and 96-like measurement cohort
sets. They must prove the Coinalyze gross/retained/new equation and projected receipt
count, exact final receipt size, stable fixed-target rerun under changed observations,
individual largest partition, integer-only lifecycle conversion, and streaming no-follow
publication. Do not reduce coverage merely to make assertions pass.

Claude runs no test, linter, control, Git, network, sizing, acquisition, or data command;
does not edit records, data, or any path outside the exact three-path drop; returns the
three corrected SHA-256 hashes and test-function count; and stops for reviewer inspection.

Hermes remains unauthorized. No integration, sizing execution, Gate 2 acceptance, bulk
acquisition, normalization, catalog publication, NautilusTrader, Harmonic Trader, payoff,
PAPER, LIVE, paid source, reduced scope, or next-ticket work is authorized.
