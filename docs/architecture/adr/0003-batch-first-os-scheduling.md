# ADR-0003 — Batch-first with operating-system scheduling

**Status:** Accepted

## Decision

Implement idempotent CLI jobs and schedule them with systemd/cron/Task Scheduler. Do not deploy an orchestration server in v1.

## Rationale

Daily/weekly research does not require a distributed scheduler. Fewer services reduce operational risk and resource use.

## Revisit trigger

- more than one machine;
- dozens of interdependent daily jobs that cannot be represented safely by the CLI dependency graph;
- multi-user queueing requirements;
- measured operational failures caused by the simple scheduler.
