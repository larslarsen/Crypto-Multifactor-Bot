# REVIEW-0064 - AUD-004 MYPY BASELINE REQUIRED

**Ticket:** AUD-004 - Native headerless support for the Binance archive precision comparator
**Status:** CHANGES_REQUIRED - JR DIAGNOSTICS AND BASELINE EVIDENCE
**Next required actor:** Jr Dev - Hermes
**Next ticket authorized:** `NONE`
**Date:** 2026-07-20

## Decision

AUD-004 remains unaccepted. The final submission truthfully records a failing mypy command, but it
labels all 12 diagnostics pre-existing without supplying the diagnostics or a pre-AUD-004 baseline.
That claim is not yet reviewable.

The command includes unchanged `tests/test_audit_runner_sprint003.py`, so a historical typing debt
must not automatically become AUD-004 scope. Conversely, any new diagnostic introduced by the
runner boundary correction must be resolved before acceptance.

## Required Evidence

Jr Dev - Hermes must:

- record all 12 diagnostics exactly, including path, line, error code, and message;
- run the identical mypy command against the parent of the first AUD-004 implementation commit in
  an isolated baseline worktree using the same environment;
- provide a deterministic current-versus-baseline diagnostic comparison;
- identify every added, removed, or changed diagnostic;
- rerun the six current acceptance gates and keep their exact evidence.

If AUD-004 adds no mypy diagnostic, return `AWAITING_REVIEW` with the no-new-errors evidence. If it
adds any diagnostic, return `BLOCKED` with the exact delta for reviewer source-task routing. Do not
broaden the ticket to repair unrelated historical typing debt.

The repository task is `docs/reviews/AUD-004_JR_MYPY_BASELINE_TASK.md`.
