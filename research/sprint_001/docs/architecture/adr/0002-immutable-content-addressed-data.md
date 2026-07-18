# ADR-0002 — Immutable, content-addressed data

**Status:** Accepted

## Decision

Raw objects, canonical datasets, and experiment bundles are immutable and identified by cryptographic hashes/manifests. Corrections create new versions and supersession edges.

## Rationale

Mutable “latest” files make historical experiments irreproducible and can silently change past results.

## Consequences

- Additional disk use.
- Explicit compaction and retention policy.
- Exact lineage and reproducibility.
- Promotion aliases may change; underlying artifacts do not.
