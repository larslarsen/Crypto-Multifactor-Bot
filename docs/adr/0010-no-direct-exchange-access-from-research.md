# ADR 0010 — Research code cannot access exchanges directly

- **Status:** Accepted
- **Date:** 2026-07-18

## Decision

Network access to exchanges and market-data providers is restricted to source adapters in the Data Platform and broker adapters in the Execution Platform. Research code consumes immutable accepted dataset IDs only.

## Enforcement

- package dependency check;
- review rule against HTTP/broker imports in research packages;
- network-denied research tests where practical;
- secrets are not available to research jobs.
