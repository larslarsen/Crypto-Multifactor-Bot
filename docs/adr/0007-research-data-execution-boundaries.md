# ADR 0007 — Enforce Data, Research, and Execution boundaries

- **Status:** Accepted
- **Date:** 2026-07-18

## Context

The legacy project mixed data access, feature computation, model evaluation, and serving concerns. This made reproducibility and parity difficult to establish.

## Decision

Use three logical layers inside the modular monolith: Data, Research, and Execution. Dependencies flow upward only. Research never accesses exchanges or credentials. Execution consumes only promoted artifacts and approved Data Platform outputs.

## Consequences

- additional interfaces and manifest handoffs;
- easier replay and testing;
- fewer accidental live-data dependencies;
- layer-import checks become part of CI;
- any alternate path requires a new ADR.
