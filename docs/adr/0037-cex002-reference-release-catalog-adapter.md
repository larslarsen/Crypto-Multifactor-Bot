# ADR 0037 — CEX-002 reference release and atomic catalog admission

Status: Accepted
Ticket: CEX-002
Reviewer: Lead Quantitative Finance Researcher/Engineer
Implements: ADR-0024 section 4; ADR-0017 platform boundary

## Problem

The ten accepted CEX-002 products already own their immutable partitions. The generic
DatasetPublisher makes independent copies and SqliteDatasetCatalog.register_from_receipt
commits one dataset at a time. Neither operation supplies the bounded, complete-release
admission required by ADR-0024. Hard links would introduce shared-inode mutation risk.

## Decision

Add a CEX-specific reference-publication adapter in the catalog layer. Preserve the
generic publisher, tree verifier, canonical manifest format, registration API and SQL
schema. The adapter uses the existing dataset, dataset_file and dataset_input_dataset
tables and one transaction. No replacement catalog or additional raw acquisition is needed.

The adapter uses existing DatasetManifest models and canonicalization to compute real
ds_ identifiers. Its named transform/protocol distinguishes reference publications from
generic self-contained dataset trees. File paths are canonical paths relative to the
explicit repository data anchor. Manifest and publication URIs use that same anchor.
The adapter's independent verifier authenticates those references; it never calls the
generic tree verifier with a fabricated publication receipt or weakens that verifier.
Generic self-contained publication behavior remains unchanged. CEX consumers use the
explicit CEX release reader, including when the generic resolver supplies a dataset ID.

Each of the ten product manifests pins the complete accepted artifact set, including
data, typed/quality gaps, lineage, completion and referenced report/manifests. Existing
Parquet files are referenced in place, with hashes, bytes, actual footer row counts and
Arrow schema identities. JSON/provenance files are identified as metadata with table row
count zero. Catalog statistics sum the declared physical table rows and bytes; separate
quality metadata preserves each product's main data count, gap counts and component
semantics. Raw provenance remains in the authenticated native lineage/receipt chain;
the adapter does not invent raw_object catalog rows or unresolved foreign keys.

The eleventh manifest describes the new typed harmonic-bundle Parquet and depends on
all ten product dataset IDs. Bundle rows contain real publication values, not sizing
placeholders, and do not recursively describe the bundle itself. No accepted input is
copied, linked, converted, repaired, recataloged under a different economic meaning, or
modified. New files are limited to bundle data and release metadata.

## Preparation and consumer proof

Preparation publishes content-addressed bundle data, canonical product/bundle manifests
and an immutable prepared descriptor. It creates no consumable catalog rows. A prepared
descriptor is explicitly not a published release. The clean NautilusTrader checker can
read this exact candidate for validation without making it visible to research readers.

Final admission requires an explicitly pinned successful consumer proof for the exact
prepared descriptor. The final immutable publication descriptor binds both hashes and
the eleven dataset identities. This avoids a circular dependency between a candidate's
identity and its subsequent consumer result. The proof must identify its checker source
and Nautilus version, enumerate every required input/component, and reconcile file/row,
time and value identities. A PASS token or a sample-only comparison is insufficient.
The reviewer supplies the accepted proof/checker hashes in the later exact publication
command; the adapter verifies those pins, proof structure and candidate bindings.
The current source assignment does not implement or run that external consumer checker.

## Admission and replay

Reauthenticate all inputs, schemas, manifest identities and consumer proof before
BEGIN IMMEDIATE. Capture file identity snapshots and recheck them at admission. Refuse
unsafe paths, symlinks, changed content, incomplete authority, dirty source identity,
conflicting dataset rows or caller-owned pending transactions. The same transaction
rechecks that the five accepted BitMEX false-authority rows remain rejected and excluded
from default resolution. It inserts all eleven datasets/files/dependencies or none.
All dependencies exist before insertion of the bundle's dependency edges.

The immutable publication descriptor is durable before SQL commit. Catalog commit is
the sole visibility gate; no post-commit filesystem marker is needed for correctness.
A crash before commit leaves only non-consumable prepared artifacts. A crash after
commit leaves the complete durable release. Readers require the exact eleven rows,
their common publication descriptor, full manifest/file/dependency agreement, the
consumer proof and accepted authority pins. Partial, stale or mixed-bundle state fails.
Replay reauthenticates and compares every persisted field and complete file/dependency
set, including bookkeeping timestamps, and reuses only an identical publication.
Do not update, supersede or repair a conflicting existing dataset.

## Limits and unchanged semantics

Use bounded streaming hashes, Parquet footers and one bundle row group at a time;
never load accepted price/OI/cost history into whole-product row lists. Metadata may be
indexed with explicit finite bounds. Account for new metadata, SQLite/WAL growth and
owned temporary files against Receipt 258's remaining release metadata allocation;
preserve its operating reserve. The bundle has its existing typed schema and allocation.

Pin the holdout, source/config/schema/code identities, observed versus full-cadence
intersection counts, source-availability unknowns, fee scenarios and observed/censored
liquidations. No fabricated vintage, rate, fee, mapping, zero flow or complete-liquidation
claim is permitted. This adapter changes no product economics or accepted acquisition.
Nautilus consumer validation, remaining economic evidence and final ticket acceptance
remain mandatory. Preparing source or a candidate does not accept Gates 3-5 or CEX-002.
