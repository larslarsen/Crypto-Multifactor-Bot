# REVIEW-0076 - RAW-002 FINAL TEST AND GATES REQUIRED

**Ticket:** RAW-002 - Harden publication-receipt verification against symlink substitution
**Status:** RESOLVED
**Next required actor:** Jr Dev - Hermes
**Next ticket authorized:** `NONE`
**Date:** 2026-07-20

## Decision

The approved source remains valid. Final acceptance is withheld for one remaining fixture defect
and false gate evidence.

## Findings

- The parent-symlink test replaces the canonical `cd` directory with a symlink to `outside`, but
  writes the target object at `outside/cd/<hash>`. Following the symlink requests
  `outside/<hash>`, which is missing. The test therefore does not model a valid same-content
  substituted parent path.
- The required Ruff, mypy, layer-import, and repository-control commands were not run exactly.
- The substituted broad mypy command failed with one error, while the handoff and report claim all
  gates passed.

No production-source changes are authorized. Jr Dev - Hermes owns the exact correction under
`docs/reviews/RAW-002_JR_FINAL_GATE_TASK.md`.
