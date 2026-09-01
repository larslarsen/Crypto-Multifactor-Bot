# ADR 0034 — Direct Recovery of the Accepted Pending Raw Objects

- **Status:** Accepted
- **Date:** 2026-09-01
- **Amends:** ADR-0031 sections 3 through 6 and ADR-0029 Gate-2 completion
- **Evidence:** `research/sprint_004/412_CEX002_DURABLE_V3_CONTINUATION_RECORD.md`

## Context

CEX-002 exists to deliver usable research data. Gate-2 generation 0 already contains the
authenticated history for 685,642 completions, including 685,072 Binance objects and 570
Coinalyze completions. Its exact remaining Binance set is the accepted v3 candidate: 51,275
objects and 9,207,379,061 listed bytes.

ADR-0031 required new acquisition code, a transition tool, and a linked replacement generation
before those bytes could be retrieved. None of that implementation exists. It would preserve
receipt lineage, but it would not improve or transform the provider bytes. Making it a
prerequisite has blocked the actual data deliverable.

An interrupted, unauthorized standard-tool retrieval also left 1,815 files occupying about
8.1 GiB under `data/harmonic_trader_source`. Those files are neither accepted nor discarded.
They are recoverable staging inputs only if each one independently matches the accepted v3 size
and provider SHA-256.

## Decision

### 1. Preserve completed authority

Generation 0 and all existing raw content, databases, receipts, sidecars, candidates, and
evidence remain unchanged. The old `plan`, `acquire`, `replay`, and `verify` commands remain
closed. No linked replacement generation or transition program will be built.

### 2. Accept one fixed recovery manifest

The v3 candidate with semantic SHA-256
`a064fec30853eba8792052e65bbb6223224e23fc7f57879ef01291f7e825ad1b` is the sole authority
for direct recovery. Its compressed 51,275-row manifest is
`data/cex002_qualify/gate2_revision_candidate_v3/manifest/4dacaba97c17ad9c4a9724f5db74dfab7ee98760cdb3df6dea46ab37c0684c2d.json.gz`.
Its exact listed-byte sum is 9,207,379,061. No relisting, scope expansion, live checksum
substitution, or additional selection is permitted.

### 3. Recover provider bytes with standard tools

Hermes owns the data mutation and execution. It must first prove that no acquisition or planner
process is live. If `data/cex002_recovery` is absent and `data/harmonic_trader_source` exists, it
may rename that staging root to `data/cex002_recovery` on the same filesystem. It must stop if
both roots exist.

Hermes must derive an ordinary URL list and GNU `sha256sum` manifest directly from the accepted
v3 rows with `gzip` and `jq`. Every destination must be the row's relative Binance key beneath
`data/cex002_recovery`; path traversal, absolute paths, and rows outside the two accepted
`daily/metrics` and `daily/bookTicker` families are refused.

Existing files receive no credit until their exact byte size and provider SHA-256 match. A
partial file may be resumed. A complete mismatch is moved to a quarantine path and retained,
then downloaded again. Missing or partial files may be fetched from the row's fixed Binance URL
using resumable standard `wget`, with at most eight concurrent requests. The same operation can
be rerun after interruption; matching files are skipped and incomplete files are resumed. No
custom downloader, planner, state database, transition tool, source edit, or test edit is
authorized.

Recovery is complete only when all 51,275 relative paths exist, each exact listed size matches,
every `sha256sum -c` row passes, and their byte sum is exactly 9,207,379,061. The provider digest
authenticates the raw ZIP bytes. ZIP member parsing and CRC validation occur when the bytes are
converted into tables; uncompressed expansion is not a reason to reject an authentic raw ZIP at
the download boundary.

### 4. Close Gate 2 without rewriting history

Hermes publishes one concise recovery record containing the start/end counts and bytes, exact
standard commands, final checksum result, any quarantined paths, and any unresolved identities.
The record reconciles:

- 685,072 accepted generation-0 Binance completions;
- 51,275 accepted v3 recovery objects;
- 570 accepted Coinalyze completions; and
- 202 already typed Coinalyze gaps.

The recovery root supplements generation 0; it is not inserted into or misrepresented as part of
generation 0. The reviewer may accept Gate 2 when the exact reconciliation and all recovery
checks pass. A provider object that no longer matches its accepted digest blocks only that exact
identity and does not authorize another planning system.

### 5. Usable tables are the next deliverable

After Gate-2 acceptance, CEX-002 proceeds directly to converting the accepted raw files into its
declared research tables. Any later source authorization must name the concrete output table and
must be accepted against real recovered input. New acquisition frameworks, generic scaffolding,
and model or trading-engine work remain out of scope.

## Consequences

- Valid completed work is preserved.
- The recovery loses no market observation and changes no market value.
- Recovery provenance consists of the accepted listing facts, provider checksum, exact size,
  relative path, and the Hermes execution record rather than a linked SQLite receipt chain.
- The project returns to measurable progress: verified raw files first, usable tables second.

