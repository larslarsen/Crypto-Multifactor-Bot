# RFC-001 — Architecture Freeze (v1)

**Status:** Frozen (RFC). Changes require an ADR (see ADR-0007).

## Purpose

This document freezes the v1 system architecture so that implementation work
proceeds against a stable, reviewable design rather than a moving target. From
this point, the architecture is treated as a **Request for Comments**: open to
challenge through the ADR process, not through silent edits.

## What is frozen

The complete v1 architecture as recorded in:

- [`docs/architecture/00_SYSTEM_ARCHITECTURE.md`](docs/architecture/00_SYSTEM_ARCHITECTURE.md)
  — system architecture (modular monolith, data/control/repository planes,
  domain boundaries, batch pipeline, research execution, serving, observability,
  acceptance gates).
- [`docs/architecture/`](docs/architecture/) — the 11 architecture docs and the
  ADR set.
- [`docs/architecture/adr/`](docs/architecture/adr/) — accepted decisions
  0001–0007.

This corresponds to the architecture accepted in commit `ff1300c`
("docs: accept research-driven architecture v1").

## Change control

1. The architecture is **frozen**. Do not edit the architecture documents
   directly to reflect a new design.
2. To change architecture, write a **new ADR** (`0008`, `0009`, …) that states
   the decision, rationale, consequences, and what it amends or supersedes.
3. Register the new ADR in [`docs/architecture/adr/README.md`](docs/architecture/adr/README.md).
4. An architecture-doc diff without a corresponding ADR reference is rejected
   in review.

This discipline is itself recorded as
[ADR-0007](docs/architecture/adr/0007-architecture-freeze-and-rfc-process.md).

## Scope note

Freezing the architecture does **not** freeze the research record. The Sprint 1
specification package (`research/sprint_001/`) remains the living research
contracts; factor cards, experiment registries, and validation protocols evolve
through their own review process. Only the *system architecture* is frozen here.
