# ADR 0038 — Shared schema contracts for CEX reference manifests

Status: Accepted
Ticket: CEX-002
Reviewer: Lead Quantitative Finance Researcher/Engineer
Implements: ADR-0037 resource and schema-identity requirements

## Evidence

The first preparation that passed all ten product accounts wrote its 13,232,150-byte
bundle object, then stopped with a calculated metadata charge of 7,450,831,574 bytes
against the unchanged 4,985,471,619-byte remainder. No candidate was sealed or admitted.
The adapter repeats a full Arrow field contract in every table file's partition JSON;
its conservative SQLite reservation also charges those repeated bytes. The detailed
SQLite/manifest subtotals were not emitted, so this decision does not invent them.

## Decision

Intern table schema contracts once per CEX dataset manifest. Keep canonical generic
DatasetManifest/OutputFileSpec models, SQL tables and generic publication behavior
unchanged. This is a CEX reference-protocol representation change, not a product-schema
or financial-semantics change. Advance the CEX transform protocol version explicitly;
there are no admitted CEX reference releases or completed v1 candidates to migrate.

Store a versioned, bounded schema registry in the identity-bearing quality summary.
Registry keys are SHA-256 hashes of the exact canonical ordered field contracts.
Each table-file partition records its schema reference instead of repeating the fields.
The file remains identity-bound to that contract through the manifest's complete
canonical identity. Metadata files retain kind=metadata and zero table rows.

Producer and reader must reject missing, malformed, mixed inline/reference, unbound or
hash-mismatched contracts. Resolve every reference before checking the actual Arrow
footer, including publication, readback and replay. Preserve type/field order/nullability,
dictionary representation, decimal precision/scale and the existing accepted list-type
normalization. A hash token without its authenticated full contract is insufficient.
The strict consumer-proof schema and complete logical readback obligations do not change.

The actual complete inventory is 423,446 files. Its strict per-file proof repeats three
digests plus paths/counts/time fields for every file, so the old 256 MiB metadata read
ceiling must not be assumed to fit. Set a finite 512 MiB proof read ceiling, keeping
the strict proof schema unchanged. The large-inventory regression must account for
the encoded representative complete proof and reserve the full finite proof ceiling
in its capacity scenario. This is a read bound, not a new storage allocation: all
actual proof bytes still consume the same release metadata remainder.

Keep the existing SQLite reservation formula/multipliers, metadata allocation, bundle
file cap and operating reserve unchanged. Include registry bytes once in actual manifest
and SQLite quality-summary accounting, and each reference in file-row accounting.
Expose charged subtotals on future resource refusal so another full run is unnecessary
merely to identify the charge. Do not solve this defect by weakening the reserve.

## Consequences

All CEX identities are regenerated under the new committed code/protocol, while accepted
source artifacts remain byte-identical. Tests must demonstrate complete contract binding,
tamper rejection through admission/read/replay, unchanged logical proof values, and a
large representative inventory whose complete conservative charge fits the fixed remainder.
Integration and real execution remain separately assigned to Hermes by the reviewer.

The failed attempt's sole unreferenced bundle object is preserved for now. Its future
disposal or retention needs an exact reviewer-assigned Hermes action before another
bundle run: a new code identity changes component IDs and therefore bundle bytes, and
two 13.2 MB objects could exceed the fixed bundle-object cap. This ADR assigns no cleanup.
