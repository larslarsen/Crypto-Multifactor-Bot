# ADR 0022 - Path-Bound Retained Checksum Recovery

- **Status:** Accepted
- **Date:** 2026-08-22
- **Amends:** ADR-0020 retained-evidence recovery and ADR-0021 frozen sizing authority
- **Evidence:** `research/sprint_004/196_CEX002_SIZING_AUTHORITY_FAILURE_ARCHITECTURE.md`

## Context

A Binance checksum sidecar contains a digest and an object basename, not the complete S3
key. The same basename can occur under several physical families. In particular,
`klines`, `indexPriceKlines`, `markPriceKlines`, and `premiumIndexKlines` use the same
`SYMBOL-1h-DATE.zip` basename shape.

The accepted recovery implementation indexed retained sidecars by basename and considered
a name ambiguous only when more than one retained sidecar with different bytes happened to
be present. Absence of a competing sidecar is not proof of a unique full key. The accepted
checkpoint consequently maps some retained premium-index ZIPs and sidecars to index-price,
mark-price, or ordinary-kline keys with the same basename.

The defect does not change the accepted unique-byte storage credit: the ambiguous aliases
refer only to digests already supported by fresh, exact-key acquisition. It does make 17
logical Kline keys falsely consumable in the acquisition manifest. Those mappings cannot
authorize reuse or suppress later acquisition.

## Decision

Retained evidence is authoritative for a full object key only when its provenance binds
that full key. A basename-only legacy sidecar may be recovered only when that basename
maps to exactly one full key in the complete frozen candidate domain. Presence of only one
retained sidecar is not uniqueness evidence.

New recovery and every reuse of a persisted `recovered_from_retained_bytes` checkpoint row
must apply the same candidate-domain collision rule. An ambiguous legacy row is excluded
from planning, acquisition-manifest consumability, storage credit, and source evidence. It
must remain preserved as rejected lineage or be removed only by an explicit reviewed
authority transition; it is never silently relabeled as valid.

Storage accounting distinguishes three quantities:

- logical requirement keys with valid retained authority;
- unique content-addressed retained objects; and
- the bytes of those unique objects.

Duplicate bytes are credited once only after at least one valid full-key binding survives.
The corrected accepted-data expectation is 73 valid requirement keys, 73 unique retained
objects, and 5,225,416 unique bytes. Of those keys, 56 belong to the selected archive
manifest and 17 belong to the complete cost sample. The 17 ambiguous Kline aliases add no
object and no byte credit and must not be marked consumable.

The frozen 96-object Gate-1 cohort contains none of the ambiguous Kline substitutions. Its
two recovered entries are basename-unique `bookTicker` objects. The Gate-1 source finding
therefore remains accepted, but report 62 and its manifest detail cannot authorize sizing
or acquisition until a corrected authority publication supersedes their affected fields
and identities.

## Consequences

Qualification source and tests must implement collision-safe recovery and deterministic
handling of already-persisted ambiguous legacy rows. The corrected authority transaction
must preserve the old checkpoint, report, and manifest as lineage, publish new immutable
identities, and prove that no network request is needed unless the corrected frozen plan
itself lacks a valid required sample.

The sizing implementation and its current pins remain frozen until the corrected report,
manifest, checkpoint, and credit decomposition are executed and accepted. Gate 2 remains
unaccepted. No invalid retained mapping may be repaired by changing a constant, accepting
the manifest-only 763,304-byte value, or treating an ambiguous basename as a full-key
identity.
