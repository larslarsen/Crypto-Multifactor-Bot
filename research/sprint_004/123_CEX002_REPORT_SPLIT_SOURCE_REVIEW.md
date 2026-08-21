# CEX-002 Report Split Source Review

Date: 2026-08-21

Reviewer: Lead Quantitative Finance Researcher/Engineer

Reviewed base: `444f26f343cec46a11c4c7d09a7b337426168f0f`

Subject review: `research/sprint_004/122_CEX002_TERMINAL_REPORT_ARCHITECTURE_REVIEW.md`

Reviewed hashes:

| Path | SHA-256 |
|---|---|
| `src/cryptofactors/acquisition/binance_usdm_harmonic_qualification.py` | `4063244fb695e91927197a9a1673367ce2689297f03505100f4cc529276061b5` |
| `scripts/research/qualify_binance_usdm_harmonic_sources.py` | `b4e9235406be5276619b4a69017ddb87a8cffefb691c2673f2e3b875cc775d96` |
| `tests/acquisition/test_binance_usdm_harmonic_qualification.py` | `c0586f3d7157339d9e8f4f1e0010bc573c2bfa1e2a768755b7e54f8a332adcc2` |

The CEX test source contains 194 uniquely named test functions. The preserved oversized
report still has SHA-256
`46d1980ecf384874e45c4c31f142c16efc5472ef63231e9456e264f3e94ef691`.
The reviewer ran no pytest, Ruff, repository-control, network, data, candidate, or
migration command.

## Decision

**REJECT BEFORE HERMES INTEGRATION. THE SPLIT-WRITER DIRECTION IS CORRECT, BUT THE
STREAMING READER EXPOSES UNVALIDATED RECORDS AND DOES NOT RECONCILE THE AUTHORITY IT
CLAIMS TO VALIDATE.**

The drop correctly removes the second in-memory manifest copy, writes deterministic gzip
detail before the compact receipt, carries an uncompressed semantic digest, enforces a
receipt ceiling, and preserves the no-migration/no-download contract. Those directions
remain required. The following defects are blocking.

## Findings

### 1. The Gate-2 iterator yields before validation completes

`iter_manifest_detail` yields every non-header record while it is still computing the
uncompressed digest, byte count, record counts, and header reconciliation. All checks run
only after the generator reaches EOF. A consumer can read one row and stop, or can act on
hundreds of thousands of rows before a final digest/count failure. That directly
contradicts its fail-closed docstring and ADR-0019's rule that Gate 2 consumes only a fully
validated contract.

Perform a complete bounded validation pass before exposing the first record. The public
iterator may make a second streaming pass only after the artifact has passed every
descriptor, encoding, header, aggregate, order, and digest check. Add a focused test whose
tamper is at the end of the artifact and whose consumer requests only the first row; the
first `next()` must raise rather than return unvalidated evidence.

### 2. Compressed identity and schema identity are not validated

The receipt records `compressed_sha256` and `compressed_bytes`, but neither
`iter_manifest_detail` nor `validate_manifest_detail` compares them with the descriptor.
The latter merely returns newly measured values. The validator also never checks the
descriptor/header `schema_version`, `format`, header `kind`, or `ticket`, and it accepts an
absolute path located under the evidence root even though the contract requires a
store-relative canonical path.

Before decompression, require the exact compressed size and SHA-256. Require all mandatory
descriptor fields and exact schema/format/header identities. Require
`relative_path == manifest_detail_relative_path(uncompressed_sha256)`, reject absolute or
non-normalized paths, and retain the root-containment check. Add direct corruption cases
for every field.

### 3. The reader trusts copied totals rather than recomputing them from detail rows

The validator proves only that selected header values equal selected descriptor values.
It does not recompute `object_count`, `compressed_raw_bytes`, `consumable_object_count`, or
`family_object_counts` from row records, and it does not reconcile pending-key records with
the non-consumable rows. A self-consistent but false header/descriptor therefore passes.
It also parses arbitrary JSON rather than proving each raw line is the canonical encoding
of the parsed record.

During the prevalidation pass, recompute every declared aggregate from rows, enforce
record-type phase/order and canonical line bytes, detect noncanonical order and duplicate
row keys, and reconcile the complete pending-key sequence with the non-consumable rows
without unbounded memory. A rolling digest/count over the same canonical row-order pending
sequence is acceptable. Unknown or missing row fields must fail closed, not coerce to
zero. Add tests that alter row bytes and then update both content address and copied
header/descriptor values; aggregate, order, duplicate, pending, and canonical-encoding
checks must still reject them.

### 4. Publication is not proved atomic on the actual failure boundaries

The tests inject a failure before detail publication starts and exercise the receipt-size
ceiling before its temporary file is written. They do not inject a partial detail-stream
write, detail rename failure, partial receipt write, or receipt rename failure. The
receipt uses a fixed `.partial-<name>` path with no `finally` cleanup, and neither publisher
flushes/fsyncs bytes before rename.

Use collision-safe same-directory temporary files, flush and fsync before atomic replace,
and clean temporary files on every exception. Preserve the prior receipt byte-for-byte on
every receipt failure. Add direct injected tests for partial write and replace failure on
both detail and receipt paths, including temp cleanup and the allowed valid-orphan-detail
case after receipt failure.

### 5. The alleged bounded stream sorts the full collections

`manifest_detail_records` calls `sorted` over all 733,203 rows and over the other detail
collections. That is O(n) auxiliary memory and contradicts the function's statement that
publication stays bounded however large the manifest becomes.

Canonicalize the held manifest collections once at their construction boundary, then
stream them without copying/sorting and verify monotonic canonical order while reading.
The publication path must not materialize a second full collection. Add source/test proof
that the detail writer does not call `sorted`, `list`, or another whole-collection copy on
the detailed collections.

### 6. One no-duplication assertion is vacuous

`assert rendered.count(row["key"]) == 0 or "detail" in rendered` always succeeds because
every valid receipt contains the word `detail`. Replace it with an actual contract: the
four detailed collection keys are absent from both receipt surfaces, representative
selected keys absent from serialized receipt bytes, descriptor present exactly where
declared, and the in-memory manifest unchanged.

## Claude correction authorization

Sr Dev - Claude Build using Claude Opus 5 is authorized to correct only the same three
paths:

- `src/cryptofactors/acquisition/binance_usdm_harmonic_qualification.py`;
- `scripts/research/qualify_binance_usdm_harmonic_sources.py`; and
- `tests/acquisition/test_binance_usdm_harmonic_qualification.py`.

Claude preserves the accepted split-publication direction and closes all six findings.
It may refactor the new ADR-0019 writer/reader code and manifest-construction ordering as
needed, but it must not change the source universe, selected rows, financial semantics,
plan, budget, retry, checkpoint, secret, no-download, exit-status, or unrelated test
contracts. It adds no dependency, Git LFS, external service, truncation, sampling, or
fallback that accepts missing detail.

The current 1.06 GB report and every data/checkpoint/cache/journal/progress path remain
frozen. Claude performs no test, Ruff, repository-control, network/data run, candidate
execution, integration, record edit, ADR edit, Git operation, commit, push, plan migration,
sample acquisition, Gate 2, catalog, Nautilus, Harmonic Trader, payoff, PAPER, LIVE, or
other-ticket work. It stops for reviewer source inspection with exact hashes for the three
authorized paths and the unique CEX test-function count. Hermes remains unauthorized.

## Reviewer publication

The reviewer publishes exactly:

- `docs/handoff/CURRENT_TASK.md`;
- `research/sprint_004/123_CEX002_REPORT_SPLIT_SOURCE_REVIEW.md`; and
- `tickets/CEX-002.md`.

No source/test path, oversized report, data, checkpoint, cache, journal, database sidecar,
or unrelated dirty path belongs to this publication.

## Disposition

CEX-002 remains `IN_PROGRESS`. Gate 1 has not passed. Integration, report rerun, plan
migration, sample acquisition, Gate 2, normalization, catalog publication, Nautilus work,
Harmonic Trader work, payoff analysis, PAPER, LIVE, and every other ticket remain
unauthorized. Next ticket remains `NONE`.
