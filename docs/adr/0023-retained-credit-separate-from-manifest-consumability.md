# ADR 0023 - Retained Credit Is Separate From Manifest Consumability

- **Status:** Accepted
- **Date:** 2026-08-22
- **Amends:** ADR-0021 sizing authority and ADR-0022 retained decomposition
- **Evidence:** `research/sprint_004/221_CEX002_REAL_AUTHORITY_DECOMPOSITION_REVIEW.md`

## Context

ADR-0022 correctly requires path-bound retained authority and separates valid logical
requirement keys, unique content digests, and unique credited bytes. It incorrectly states
that the accepted 73 valid requirement keys decompose into 56 selected-manifest keys and
17 complete-cost keys.

That split was inferred by subtracting the manifest's 56 `consumable=true` rows from the
Gate-2 credit total. The two quantities have different publication boundaries. Manifest
consumability is fixed when the selected manifest is built from objects re-proved before
that construction step. Gate-2 retained credit is computed later over the complete
selected-plus-cost requirement and re-proves every effective checkpoint row it considers.
It can therefore prove a selected requirement key whose manifest row conservatively
remains `raw_validation_pending`.

The corrected report itself does not claim a 56/17 credit split. It separately reports 56
manifest-consumable rows and 73 valid Gate-2 requirement keys. Record 218 and reviews 219
and 220 incorrectly interpreted their difference as complete-cost credit.

Read-only intersection of the pinned report, 733,203-row manifest, 3,144-key complete-cost
set, path-bound rejected-key set, and pinned 440-row checkpoint proves:

- 56 selected manifest rows are marked consumable;
- 68 effective checkpoint keys belong to the selected archive requirement;
- 5 effective checkpoint keys belong to the complete-cost requirement;
- 68 plus 5 equals the report's 73 valid retained requirement keys; and
- the 12 selected effective keys not marked manifest-consumable are six daily metrics and
  six monthly funding-rate objects.

The report's canonical retained-credit helper rehashed all 73 objects and their provider
sidecars, found zero unverified objects, deduplicated to 73 unique digests, and credited
5,225,416 bytes. The total credit and projected 20,351,715,427 new Binance raw bytes remain
correct. The error is the inferred family split and the assumption that manifest
consumability is the sole Gate-2 credit authority.

## Decision

Manifest consumability and Gate-2 retained credit remain separate, explicitly named
authorities:

1. **Manifest consumability** is the immutable selected-manifest publication fact. The
   accepted count is 56. It controls what that manifest already calls immediately
   consumable; it is not the Gate-2 storage-credit key set.
2. **Gate-2 retained credit** is independently re-proved over the union of all 733,203
   selected archive keys and all 3,144 complete-cost keys. A checkpoint row earns credit
   only if its full key belongs to that requirement, it is not rejected path-bound
   lineage, any basename recovery binds uniquely, and its object, sidecar, and declared
   size re-prove against current bytes.
3. The accepted current Gate-2 split is 68 selected retained keys and 5 cost retained
   keys. These are logical-key counts. Unique objects remain 73 and unique bytes remain
   5,225,416.
4. No consumer may infer either side of the credit split by subtracting manifest
   consumability from total credit. It must classify the re-proved full keys by membership
   in the selected and complete-cost requirement sets.
5. Duplicate valid keys count separately as logical keys but each content digest earns one
   object and one byte charge. A rejected or unverifiable binding earns neither key,
   object, nor byte credit.

The sizing receipt must publish all of these separately: manifest-consumable selected
keys, selected retained-credit keys, cost retained-credit keys, total valid requirement
keys, unique objects, unique bytes, rejected lineage rows, and unverified objects.

## Consequences

Gate 1 remains accepted. No source, report, manifest, checkpoint, or retained-data rewrite
is required. The total physical requirement, retained credit, projected new raw bytes,
source qualification, and budget accounting are unchanged.

The sizing source and tests must replace the incorrect selected-consumable-as-credit rule
with the complete selected-plus-cost requirement intersection, pin 56 only as the separate
manifest fact, and reproduce the accepted 68/5/73/73/5,225,416 decomposition before any
envelope publication. The correction remains local and network-free and authorizes no
acquisition or gate acceptance.
