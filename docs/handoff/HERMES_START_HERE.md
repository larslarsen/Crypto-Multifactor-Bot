# Governing instructions for Hermes

You are implementing a local-first quantitative research platform on one Ryzen 5600X with 32 GB RAM. Correctness, point-in-time integrity, reproducibility, and auditability dominate speed and feature count.

## Read before editing

Read, in order:

1. root `README.md`;
2. research charter and validation protocol;
3. system and data architecture;
4. ADRs 0001–0010;
5. `docs/architecture/11_LAYER_BOUNDARIES.md`;
6. `docs/architecture/12_EVIDENCE_REGISTRY.md`;
7. the assigned ticket only.

## Non-negotiable rules

- Implement one ticket at a time.
- Do not add services, daemons, cloud dependencies, databases, frameworks, or queues without an approved ADR.
- Do not implement factors, models, backtests, or exchange execution before the data foundation exit gates pass.
- Research modules never call exchange APIs, read API keys, instantiate HTTP clients, or import broker adapters.
- Execution modules never become an alternate historical data path.
- Raw source bytes are immutable and content-addressed.
- Canonical and derived datasets are immutable and identified by manifests.
- Labels are physically and logically separated from features.
- Do not use `latest.*` filenames as identity or promotion controls.
- Do not silently impute missing values, repair bad observations, or continue after failed quality gates.
- Do not introduce global mutable state.
- Do not hard-code local paths.
- Do not use pandas for full historical datasets; use Polars/PyArrow/DuckDB and bounded batches.
- SQLite holds metadata, never large observations.
- Every external side effect must be idempotent or explicitly recorded.
- Every accepted change includes tests and documentation.

## Working method

For each ticket:

1. restate the ticket invariants in your own words;
2. inspect existing code and identify exact files to change;
3. write or update tests first where practical;
4. implement the smallest solution that satisfies the ticket;
5. run formatter, linter, type checker, and tests;
6. provide a compact change report including commands run and unresolved risks;
7. stop. Do not start the next ticket.

## Prohibited shortcuts

- no fake data presented as empirical evidence;
- no backfilled universe from current listings;
- no future-derived thresholds;
- no train/test shuffling for time-series research;
- no row-level random cross-validation;
- no broad `except Exception: pass`;
- no deletion or overwrite of prior manifests or decision events;
- no committing raw market data, API secrets, local databases, or model binaries;
- no architecture refactor hidden inside a feature ticket.

## Repository control plane

This repository uses a control plane, not an autonomous workflow:

- There is no self-driving or autonomous ticket progression.
- Development agents do not push, inspect remotes, or verify public GitHub state.
- The owner publishes commits.
- Exactly one ticket is active at a time.
- Development agents commit locally and stop; only the owner or a designated reviewer
  accepts work or authorizes the next ticket.
- Chat instructions are not durable state until recorded in the repository.

## First assignment

Always follow the ticket named in `docs/handoff/CURRENT_TASK.md`. Never hard-code a ticket ID in this file.