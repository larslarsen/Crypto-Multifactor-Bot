# Architecture Decision Records

Indexed, monotonic, and living. This file is the single source of truth for
accepted architecture decisions. Update it alongside every new ADR.

## Process (established by ADR-0007)

The architecture (`00_SYSTEM_ARCHITECTURE.md`, v1) is **frozen as RFC-001**.
Any change to architecture — components, domain boundaries, data flow,
technology, or repository layout — requires a **new ADR**. Silent edits to the
architecture documents are prohibited; an architecture-doc diff without a
corresponding ADR reference is rejected in review.

New ADRs take the next number (`0008`, `0009`, …), carry a `Status`, and link
what they amend or supersede.

## Register

| ADR | Title | Status | Amends / Supersedes |
|---|---|---|---|
| [0001](0001-local-parquet-duckdb-sqlite.md) | Local Parquet + DuckDB + SQLite | Accepted (provisional, pending size audit) | — |
| [0002](0002-immutable-content-addressed-data.md) | Immutable content-addressed data | Accepted | — |
| [0003](0003-batch-first-os-scheduling.md) | Batch-first OS scheduling | Accepted | — |
| [0004](0004-venue-specific-canonical-adapters.md) | Venue-specific canonical adapters | Accepted | — |
| [0005](0005-no-external-research-platform-services.md) | No external research-platform services | Accepted | — |
| [0006](0006-typed-promotion-and-serving-parity.md) | Typed promotion & serving parity | Accepted | — |
| [0007](0007-architecture-freeze-and-rfc-process.md) | Architecture freeze & RFC process | Accepted | establishes this register |

## Status vocabulary

- **Accepted** — decision stands; implement against it.
- **Accepted (provisional, …)** — accepted pending a named gate; record the
  gate in the ADR.
- **Proposed** — open for comment (RFC phase).
- **Superseded by ADR-00XX** — replaced; keep for lineage.
- **Deprecated** — no longer recommended; retained for history.
