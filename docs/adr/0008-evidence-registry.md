# ADR 0008 — Add an append-only Evidence Registry

- **Status:** Accepted
- **Date:** 2026-07-18

## Context

Code and experiment tables do not preserve why hypotheses were accepted, rejected, deferred, or quarantined. Negative results can be forgotten and repeated.

## Decision

Create stable hypothesis IDs, immutable versions, evidence items, evidence links, evidence snapshots, and append-only decision events. Link empirical evidence to experiment fingerprints and dataset lineage.

## Consequences

- decisions become reviewable and historically stable;
- negative evidence remains visible;
- no one-number evidence score is used;
- a small amount of registry administration is required;
- the registry is implemented in SQLite and exported to versionable YAML/JSON summaries.
