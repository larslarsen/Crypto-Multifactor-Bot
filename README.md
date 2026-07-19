# Crypto Multifactor Platform

A local-first, point-in-time cryptocurrency research platform for building and evaluating
implementable multifactor portfolios.

## Status

- **Architecture:** frozen unless an approved ADR changes it.
- **Current implementation milestone:** control catalog and migration runner.
- **Current task:** [`AUD-001`](tickets/AUD-001.md), schema and coverage profiler.
- **Trading status:** no model is approved for serving or live capital.

This repository is the source of truth. Research, architecture, tickets, implementation,
tests, and promotion decisions must remain traceable inside the repository.

## Governing principles

1. Data integrity precedes factors, models, and execution.
2. Raw observations are immutable and content-addressed.
3. Every derived dataset is identified by a reproducible manifest.
4. Point-in-time availability is distinct from event time.
5. Research consumes immutable datasets; it does not call exchanges directly.
6. Execution consumes explicitly promoted artifacts; it does not discover `latest_*` files.
7. Hypotheses, evidence, experiments, and decisions are append-only and auditable.
8. Simple, costed baselines precede machine-learning challengers.
9. No architecture change is made without an ADR supported by a concrete problem.

## Platform boundaries

```text
External sources
      |
      v
Data layer
  ingestion -> immutable raw objects -> validation -> canonical datasets
      |
      v
Research layer
  universes -> factors -> labels -> experiments -> portfolios -> evidence
      |
      v
Execution layer
  promoted artifacts -> paper serving -> broker adapters
```

Dependency direction is enforced by the repository's layer-contract checks.

## Start here

- [Architecture RFC](docs/ARCHITECTURE_RFC.md)
- [Architecture documents](docs/architecture/)
- [Architecture decisions](docs/adr/)
- [Engineering standards](docs/engineering/)
- [Hermes handoff](docs/handoff/HERMES_START_HERE.md)
- [Current developer task](docs/handoff/CURRENT_TASK.md)
- [Implementation tickets](tickets/)
- [Research sprint](crypto_multifactor_research_sprint_v1_1/)
- [Evidence registry](research/evidence/)
- [Research Sprint 002 (2025-2026 literature refresh)](research/sprint_002/)

## Development setup

```bash
cd /home/lars/Crypto_Multifactor_Bot
uv sync --extra dev
uv run pytest
uv run ruff check src tests
uv run mypy src
```

Initialize a local control database:

```bash
mkdir -p .local
uv run cf catalog init --database .local/control.db
uv run cf catalog status --database .local/control.db
```

Local databases, downloaded data, secrets, caches, and generated experiment artifacts must
not be committed.

## Current review gate

Active ticket: [`AUD-001`](tickets/AUD-001.md) — schema and coverage profiler
(reviewer verdict `CHANGES_REQUIRED`; Sr Dev correction drop pending integration).
