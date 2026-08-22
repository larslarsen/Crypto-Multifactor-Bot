# ADR 0020 - Historical Contract Authority and Qualification Budget

- **Status:** Accepted
- **Date:** 2026-08-21
- **Amends:** ADR-0017 historical-membership authority and Gate-1 sampling
- **Evidence:** `research/sprint_004/137_CEX002_MEMBERSHIP_AND_BUDGET_ARCHITECTURE.md`

## Context

The completed Gate-1 inventory has 771 affirmatively confirmed USD-M perpetuals and 63
blocking archive-only names. Those names are not an unknown mixture:

- 46 are exact reviewed delivery identities: two `BTCBUSD_YYMMDD`, twenty-two
  `BTCUSDT_YYMMDD`, and twenty-two `ETHUSDT_YYMMDD` names; and
- 17 are exact reviewed settlement-suffixed archive aliases mapping to 16 already-confirmed
  perpetuals. `AERGOUSDT` has both single- and double-`SETTLED` aliases.

The Binance USD-M market-data reference defines `PERPETUAL`, `CURRENT_QUARTER`, and
`NEXT_QUARTER` contract types and an official quarterly-contract settlement-price endpoint,
`GET /futures/data/delivery-price`. A 2026-08-21 probe returned 18 exact quarterly delivery
dates for each of BTCUSDT and ETHUSDT, from 2022-03-25 through 2026-06-26. It returned no
BTCBUSD history and omitted the four 2021 BTCUSDT/ETHUSDT deliveries. The endpoint is
authoritative when a record is present but is not a complete historical registry.

The retained, content-addressed official archive listings independently contain every one
of the 46 exact delivery identities across multiple market-data families and contain no
realized-funding observation for them. They also contain 1,328 objects under the 17 exact
settlement aliases. Every alias reduces to an already-confirmed base perpetual: twelve bases
have authenticated `exchangeInfo` evidence and four have official realized-funding
evidence. Treating those aliases as separate economic contracts would double-count venue
identities; silently discarding their raw provenance would also be wrong.

The candidate plan exposes a separate layering defect. The complete frozen first/midpoint/
last cost-calibration product contains 3,117 still-unretained book objects and 12,250,121,963
still-unretained compressed bytes. The implementation places that final product inside the
268,435,456-byte Gate-1 source-qualification allowance. Its lexicographic greedy selection
therefore spends 268,277,054 bytes on twenty `bookTicker` objects and blocks 78 tiny
non-cost qualification objects. The full cost product is 12,522,974,218 compressed bytes;
it belongs in Gate 2 acquisition and storage, not in the bounded Gate-1 schema sample.

## Decision

### 1. Frozen reviewed historical identities

The source publishes two explicit versioned authority tables whose exact members are fixed
by review 137:

1. 46 delivery symbols, each bound to pair, UTC delivery date, retained official archive
   evidence, funding absence, and direct settlement-price evidence when the endpoint still
   retains that date; and
2. 17 settlement aliases, each bound to one of 16 exact confirmed base perpetuals and its
   retained official archive evidence.

These are evidence tables, not regular-expression classifiers. A future `*_YYMMDD` or
`*SETTLED*` name is not automatically classified and remains blocking until a new reviewed
authority-table version is published.

The 36 delivery identities whose dates occur in current official delivery-price responses
are `official_delivery_direct`. The eight 2021 BTCUSDT/ETHUSDT identities and two BTCBUSD
identities are `reviewed_archive_delivery_inference`: their exact identities are frozen
from the reviewed official multi-family archive lifecycle and funding absence. This second
class is an explicit reviewer inference, not a claim that a retained type row or the current
settlement endpoint covers those ten names. The implementation must re-prove their frozen
archive evidence and funding absence; any mismatch remains blocking. Both classes are
delivery/non-perpetual, excluded from perpetual membership, preserved in the report, and
never treated as accepted perpetuals.

The 17 aliases are `official_archive_settlement_alias`, not separate members. An alias is
nonblocking only when its exact frozen mapping resolves to a base that independently passes
the existing affirmative perpetual rule. The raw alias name, base name, object counts,
families, byte totals, and listing provenance remain report evidence. Alias objects are not
silently promoted into the selected perpetual manifest. They remain typed, nonconsumable
alias evidence until later economic validation proves whether a non-overlapping interval
belongs to the base contract; any uncovered base interval remains an explicit product gap.

### 2. Retained source evidence

The qualifier queries only the distinct pairs required by the frozen delivery table. It
retains each official response content-addressably and reports endpoint, request pair,
retrieval time, byte count, SHA-256, parsed delivery dates/prices, and which frozen symbols
matched. Empty and retention-truncated results are evidence, not errors and not permission
to generalize from spelling.

The authority report also binds both frozen tables to a schema version and digest. It
reports every delivery and alias classification, the direct-versus-reviewed basis, and any
table/evidence/base mismatch. A mismatch fails closed before a candidate plan is built.

### 3. Qualification samples versus final acquisition

The complete cost-calibration object set remains unchanged: first, chronological midpoint,
and last whole-day `daily/bookTicker` and `daily/bookDepth` object for every accepted
contract wherever available. It retains its exact object count, bytes, digest, typed gaps,
and Gate-2 storage charge. No object is removed because it is large or because the complete
set exceeds the Gate-1 allowance.

Gate 1 instead has a distinct source-qualification plan:

1. required non-cost early/middle/recent/delisted samples are selected first;
2. for each cost family, order its available objects canonically by economic date and key,
   assign zero-based item `i` of `n` to stratum `min(2, floor(3 * i / n))`, and select the
   smallest positive-byte object in each non-empty early, middle, and recent stratum,
   breaking ties by canonical key;
3. reuse a selected object only after its retained bytes and provider checksum re-prove;
4. deduplicate physical keys across logical uses; and
5. require every selected object plus the cumulative new bytes to fit the existing
   268,435,456-byte allowance, otherwise remain blocked without truncation or substitution.

Each cost-family qualification sample must be checksum-proved, non-empty, parseable under
the declared schema, time-monotonic, and economically valid for its quote/depth fields. A
bounded sample can qualify the source contract but cannot accept the final cost product.
Final acceptance still requires acquisition, normalization, coverage, and reconciliation of
the complete frozen cost manifest.

### 4. Candidate lineage

The corrected architecture emits candidate plan version 4. Locked versions 0-2 remain
immutable. The unexecuted version-3 candidate remains preserved by its plan digest
`0a1c358c8fee3df35d1049424502b11e38c0084592a03ab6f9de99b8a0078593` and envelope
digest `a14018c27d8e00d3f59d4181d7da546ca99d43f5625c34d39cb07398859605c3` as a
superseded candidate, never as a migrated lock.

Version 4 reuses the existing 268,435,456-byte architecture-amendment allowance because
version 3 downloaded and charged nothing. Candidate construction remains read-only:
`migration_authorized=false`, `download_authorized=false`, no amendment ledger, no lock or
legacy-ledger rewrite, and empty samples. A later reviewer decision is required before any
plan mutation or sample download.

### 4a. Reviewed version-4 migration transaction

Review 145 accepts the read-only version-4 candidate at report SHA-256
`f26abbc577307e5dcef693ec159fa65d1373d7b03c2be0eb6b926e5b09f97406`.
Its plan-content digest is
`2fb0e47a3666f0e87b35dd7fdd6ea26aa352e34acf8dfd5debf590409aecbbef`,
its candidate-envelope digest is
`be63989bd4d3d40c95c7ca405eae7558ce0ef997a2289892d14ed8d773d4cbfe`,
and its complete-cost-manifest digest is
`04842ff6b9b58280b3ec2ea2644b3d44769be62d460bef785262cd4dd65cac57`.
It contains 106 entries: 84 new objects / 1,049,324 bytes, 12 retained objects /
44,642 bytes, 10 aliases, and zero blocked entries.

Migration is an explicit one-shot state transition, never a general relock facility. The
only interface is fixed to the reviewed identities above and accepts no caller-selected
plan, digest, version, allowance, ledger, relock, or download authority. Candidate-only
construction remains read-only, ordinary execution never auto-migrates, and migration
itself stops before sample acquisition.

The prior version-2 lock at SHA-256
`e04a5ce2f2513cc8a0f4e6698dcbf9d43c5a7bec0295021ca5d431ff886f0d84`
and legacy ledger at SHA-256
`47341a9ca2c60caf73485fb9bac40c6526cb35a13471e4545cd9cdcee6e227f6`
are immutable authorities. Migration first preserves the exact prior-lock bytes at a
content-addressed evidence path. It then atomically creates a prepared amendment ledger
bound to the accepted report, candidate plan/envelope, prior lock, legacy ledger,
complete-cost manifest, the `cex002_architecture_amendment_v3` allowance identity, and the
exact executing source/config identity. The separately validated amendment ledger starts
with the full 268,435,456-byte allowance and no charge or reservation.

Publishing the explicit version-4 lock is the transaction commit point. The lock preserves
locked versions 0-2 without rewriting their plan documents or digests and records the
unexecuted version-3 candidate separately by its accepted plan/envelope digests; version 3
is never installed or relabelled. The version-4 lock binds the reviewed candidate and the
prepared amendment-ledger authority. The legacy ledger remains byte-identical.

The two-file transaction is ledger-first and lock-last. A crash leaving the exact prepared
ledger with the version-2 lock authorizes no execution; only the same reviewed migration
may idempotently finish. A version-4 lock with a missing, substituted, malformed, or
authority-mismatched amendment ledger fails closed before sample transfer. Every other
partial or mixed state fails closed without falling back to the legacy ledger.

After a separately reviewed live migration, ordinary version-4 execution re-proves its
frozen plan inputs and retained evidence, replays the exact accepted keys without
re-selection, and uses only the amendment ledger for write-ahead reservation,
reconciliation, and settlement. The legacy ledger is read and rehashed only as preserved
lineage. A source/config change advances through an explicit reviewed migration receipt;
it cannot silently change selection content or conceal a changed plan-content digest.

This section fixes the implementation contract but does not itself authorize a live
migration or sample download. Source acceptance, integration, migration execution, and
sample execution remain separate reviewer gates.

### 5. Storage and scope

The current inventory reports 7,833,966,625 selected compressed raw bytes and
12,522,974,218 complete cost-sample bytes, approximately 20.36 GB before normalized data,
temporary high-water space, and operating reserve. Those later components remain unknown;
Gate 2 remains unproved. This ADR authorizes no purchase, bulk download, reduced universe,
reduced cost product, plan migration, Gate 2, model work, Nautilus execution, PAPER, or
LIVE work.

## Consequences

- The known 63 names can be resolved without pretending the current settlement endpoint is
  a complete historical registry and without accepting spelling as future authority.
- Settlement-labelled archive objects remain visible and attributable without becoming 17
  false contracts or silently contaminating base histories.
- Gate 1 validates every required source family within a bounded allowance while Gate 2
  still acquires the complete 12.52 GB cost-calibration product.
- New historical-name shapes fail closed and require explicit reviewer evidence.
