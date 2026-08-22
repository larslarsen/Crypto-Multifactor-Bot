# CEX-002 Sizing-Authority Failure Architecture

**Date:** 2026-08-22
**Reviewer:** Lead Quantitative Finance Researcher/Engineer
**Decision:** `RECORD_195_ACCEPTED_STOP_AUTHORITY_CORRECTION_REQUIRED`
**Gate 1:** Source finding remains accepted; affected publication authority is suspended
**Gate 2:** Not accepted

## Record-195 decision

Hermes's record 195 is accepted as a correct stop. Focused sizing tests, exact-path Ruff,
and repository control passed. The first local sizing invocation exited 1, the second was
not run, and receipt 180 and the sizing-envelope tree remain absent. Commit
`570b1b363b3fbc21873c4b970bb532ae2d61a178` has exactly the four authorized paths and is
aligned with `origin/main`.

The sizing failure is not cache corruption. Read-only inspection proved all pinned
top-level hashes, the 733,203-row / 7,833,966,625-byte selected manifest, and the complete
3,144-object / 12,522,974,218-byte cost set. Every content-addressed listing-cache filename
also rehashed to its bytes.

## Root cause

`prove_retained_acquisition_credit()` currently considers only the manifest's 73 rows
marked `consumable`. Their retained blobs rehash correctly but total 763,304 bytes, so the
function fails against the pinned 5,225,416-byte credit before envelope publication.

Changing that pin would be wrong. Report 62 derived the credit from every retained
checkpoint key in the selected-plus-cost requirement and deduplicated by content digest:

| Evidence set | Logical keys | Unique digests | Unique bytes |
|---|---:|---:|---:|
| Report-62 requirement intersection | 90 | 73 | 5,225,416 |
| Fresh exact-key entries | 71 | 71 | 5,021,563 |
| Recovered basename-only entries | 19 | 8 | 273,961 |
| Ambiguous recovered Kline entries | 17 | 6 | 70,108 |
| Basename-unique recovered `bookTicker` entries | 2 | 2 | 203,853 |

The six ambiguous Kline digests duplicate fresh valid digests, so excluding all 17 false
logical mappings leaves the same 73 unique objects and 5,225,416 bytes. The valid logical
decomposition is 56 selected-manifest keys plus 17 complete-cost-sample keys.

The authority defect is in retained recovery. A checksum sidecar names only a basename,
but `RetainedChecksumIndex` attributes it to any requested full key with that basename.
The index detects ambiguity only if competing sidecar bytes happen to be retained. Actual
checkpoint evidence maps one premium-index ZIP and sidecar to index-price, mark-price, and
premium-index keys. The ZIP payload is visibly premium-index data. Full-path authority was
never proved for the first two mappings.

The frozen 96-object Gate-1 sample cohort contains none of these 17 ambiguous Kline rows.
Its only two recovered entries are basename-unique `bookTicker` keys. The source finding
remains accepted, but report 62's manifest consumability and bound progress authority may
not authorize sizing or acquisition. ADR-0022 governs the correction.

## Claude source authority

Sr Dev - Claude Build using Claude Opus 5 is authorized to edit only:

- `src/cryptofactors/acquisition/binance_usdm_harmonic_qualification.py`; and
- `tests/acquisition/test_binance_usdm_harmonic_qualification.py`.

Implement ADR-0022 without hard-coding the 17 observed keys or weakening any checksum.
The complete frozen candidate-key domain, not the current cache contents, determines
basename ambiguity. Apply the rule both to new recovery and to already-persisted
`recovered_from_retained_bytes` rows before they can influence planning, manifest
consumability, credit, or source evidence. Fresh exact-key checkpoint rows remain valid.
Basename-unique recovery such as `bookTicker` remains supported.

Make the report distinguish valid retained logical keys, unique physical digests, and
unique bytes. Duplicate bytes receive one credit only when at least one valid full-key
binding survives. Preserve the accepted 73-object / 5,225,416-byte result while ensuring
the corrected selected manifest has only its 56 valid consumable keys. Preserve rejected
legacy rows as explicit lineage or support a deterministic reviewed transition; never
silently accept, delete, or rewrite them.

Add focused tests proving:

1. one retained sidecar is insufficient when its basename maps to several candidate full
   keys;
2. competing Kline-family keys cannot recover or reuse one another's bytes;
3. a persisted ambiguous recovered row is excluded from every effective authority path;
4. a fresh exact-key row with the same basename remains valid;
5. basename-unique recovery remains valid; and
6. key count, unique-object count, and unique-byte credit are separately deduplicated.

Claude runs no test, linter, control, qualification, sizing, network, data mutation, Git,
commit, push, or repository-record edit. Do not edit the sizing source or sizing tests in
this drop. Return the two SHA-256 identities, test-function count, and a concise summary,
then stop for reviewer inspection.

## Stop boundary

Gate 2 remains unaccepted. No sizing retry, qualification execution, authority mutation,
bulk acquisition, normalization, catalog publication, NautilusTrader, Harmonic Trader,
payoff, PAPER, LIVE, paid-source, reduced-scope, or next-ticket work is authorized. Next
ticket remains `NONE`.
