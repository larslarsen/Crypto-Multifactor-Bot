# ADR 0019 - Scalable Qualification Evidence Publication

- **Status:** Accepted
- **Date:** 2026-08-21
- **Extends:** ADR-0017 and ADR-0018 evidence mechanics only
- **Evidence:** `research/sprint_004/121_CEX002_LISTING_INTEGRATION_AND_CANDIDATE_RESUME.md`
  and `research/sprint_004/122_CEX002_TERMINAL_REPORT_ARCHITECTURE_REVIEW.md`

## Context

The first complete bounded CEX-002 listing run finished in 1,963 seconds. It selected
733,203 acquisition-manifest rows. The qualification report serialized those rows twice:
once at top-level `acquisition_manifest.rows` and again at
`storage.acquisition_manifest.rows`. The resulting tracked JSON was 1,059,297,547 bytes
and contained roughly 20.5 million manifest scalar values. GitHub rejected the blob under
its 100 MB per-file limit.

This is a publication-shape defect, not a reason to reduce the historical universe,
required fields, selected manifest, lineage, or source evidence. Git LFS would add a
repository-wide external storage dependency without fixing the duplicate, monolithic
representation. Treating the detailed manifest as a hand-written research document would
also contradict `.gitignore`, which keeps large/regenerable data in `data/` while Git
retains specifications, registries, decisions, and compact evidence.

## Decision

CEX-002 qualification evidence is split into two cryptographically bound layers:

1. `research/sprint_004/62_CEX002_GATE1_SOURCE_PROCUREMENT.json` remains the tracked,
   deterministic qualification receipt. It contains every low-cardinality gate,
   membership, plan, storage, coverage, lineage, retry, checkpoint, blocker, and summary
   field needed for review, but never embeds the detailed acquisition-manifest collections.
2. The complete manifest detail is written once beneath
   `data/cex002_qualify/evidence/manifests/sha256/` as deterministic canonical JSON Lines
   compressed with deterministic gzip. The artifact contains a versioned header plus all
   selected rows, collisions, rejections, and raw-validation-pending keys without loss.
3. The artifact filename is its SHA-256 over the uncompressed canonical JSONL bytes. The
   tracked receipt records the relative path, format/schema version, uncompressed and
   compressed SHA-256 values, uncompressed and compressed byte counts, record counts,
   object/byte totals, family counts, cadence rule, and integrity rule.
4. `acquisition_manifest` is the sole in-memory detailed-manifest owner. The storage block
   carries a summary/reference, not a second row copy. Semantic report identity includes
   the uncompressed detail digest and all summary counters.
5. Detail publication is streaming and bounded-memory. It may not materialize another full
   manifest serialization or call monolithic `json.dumps(report.to_dict())` on the full
   report. Records and collections are canonically ordered before hashing.
6. Detail bytes are published atomically before the compact receipt. A pre-existing
   content-addressed artifact is rehashed and structurally revalidated before reuse.
   Missing, truncated, malformed, count-mismatched, digest-mismatched, or path-escaping
   detail evidence fails closed. If detail or receipt publication fails, the prior tracked
   receipt remains byte-identical; a valid orphan detail blob is harmless immutable data.
7. The compact receipt is written atomically and must remain below a conservative
   90,000,000-byte publication ceiling. Exceeding the ceiling fails before replacement;
   it never silently drops a field or truncates evidence.
8. A streaming reader/validator must reconstruct or iterate every detailed record and
   reconcile all descriptor hashes, sizes, counts, totals, and rules. Gate 2 may consume
   the manifest only through that validated contract.
9. No Git LFS, paid storage, external artifact service, data-scope reduction, row sampling,
   lossy summary, or unverified out-of-repository reference is introduced.
10. Before a corrected candidate replaces the current oversized report, its exact
    1,059,297,547 bytes at SHA-256
    `46d1980ecf384874e45c4c31f142c16efc5472ef63231e9456e264f3e94ef691`
    must be preserved content-addressably under the ignored CEX-002 data root and rehashed.

## Required Proof

Deterministic tests must establish:

- exact detail round-trip for rows, collisions, rejections, and pending keys;
- identical semantic and compressed digests across independent roots;
- no duplicate detailed rows in the compact receipt or storage block;
- correct hashes, sizes, counts, family totals, cadence, and integrity reconciliation;
- atomic preservation of an existing receipt on every injected detail/receipt failure;
- verified reuse and rejection of missing, truncated, malformed, tampered, count-mismatched,
  path-escaping, or wrong-content-address detail artifacts;
- the 90,000,000-byte fail-closed ceiling without truncation;
- stable report identity through the detail semantic digest; and
- unchanged Gate-1 authority, candidate-plan, selected-manifest, and no-download behavior.

## Consequences

The current terminal status-2 execution remains valid performance and source evidence but
is not the final publishable Gate-1 receipt. A corrected candidate-only rerun is required
after source acceptance and Hermes integration. It must reuse the completed listing
checkpoint/cache and may not migrate a plan or download samples.

The full detailed manifest remains local immutable data, like the listing cache and raw
objects. The repository remains the authority for its schema, selection rules, compact
receipt, content identity, and review decision. Gate 1, Gate 2, Nautilus, and Harmonic
Trader work remain unauthorized until the split evidence is produced and accepted.
