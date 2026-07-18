# Current developer task

Complete [`GOV-001`](../../tickets/GOV-001.md) and stop for review.

The architecture is unchanged. This task establishes the minimal governance layer (AGENTS.md, control script, ADR process visibility) so that senior review of subsequent work can happen directly on public main.

## Governing review

Read [`ADR-0011`](../adr/0011-repo-governance-and-agent-instructions.md) and the root [`AGENTS.md`](../../AGENTS.md).

## Required outcome

- Root `AGENTS.md` exists and documents agent rules.
- `tickets/GOV-001.md` exists.
- ADR 0011 exists.
- `scripts/check_repo_control.py` exists and passes.
- `docs/handoff/CURRENT_TASK.md` points to GOV-001.
- The governance commit is visible on public `origin/main` (run `git rev-parse origin/main`).
- `scripts/check_repo_control.py` reports PASS.
- Senior can review without additional context transfer.
