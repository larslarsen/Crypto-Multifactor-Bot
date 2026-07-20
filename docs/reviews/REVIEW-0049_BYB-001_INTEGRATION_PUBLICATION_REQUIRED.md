# REVIEW-0049 - BYB-001 INTEGRATION PUBLICATION REQUIRED

**Ticket:** BYB-001 - Bybit Public Trade-Archive Normalizer
**Reviewed commit:** `f667c6d`
**Status:** CHANGES_REQUIRED - JR PUBLICATION ONLY
**Next required actor:** ~~Jr Dev - Hermes~~ -> Reviewer (resolved)
**Next ticket authorized:** `NONE`
**Date:** 2026-07-20

The source, tests, and recorded gates are not rejected. Commit `f667c6d` is pushed, but it omits
the governing BYB records referenced by `CURRENT_TASK.md`; those files remain untracked locally.
A fresh clone therefore lacks its source assignment and review history.

## Required correction

1. Add `docs/reviews/BYB-001_SR_SOURCE_TASK.md` and REVIEW-0044 through REVIEW-0049.
2. Update `docs/reviews/BYB-001_CHANGE_REPORT.md` with integration commit `f667c6d`, the
   corrective commit hash, and push/remote evidence.
3. Update README to reflect this correction and then the restored review state.
4. Do not add `.stale/`. Do not change production source or tests.
5. Run `python3 scripts/check_repo_control.py` and verify `git status --short` contains only the
   unrelated `.stale/` entry after commit and push.
6. Restore `AWAITING_REVIEW` with the reviewer as next actor, push the corrective commit, return
   its hash/evidence, and stop.

The six ticket acceptance gates need not be rerun because source and tests must remain unchanged.
This is not ticket acceptance and does not authorize another ticket.

## Resolution (satisfied)

The publication correction required here is complete:

- Corrective commit `f00c3d8` added `BYB-001_SR_SOURCE_TASK.md` and REVIEW-0044 through
  REVIEW-0049 (governing records previously omitted from `f667c6d`).
- Closing commit `cde1255` (and `5da19f8`) set the ticket, backlog, README, and handoff to
  the accepted/closed state and corrected CURRENT_TASK's next actor to Reviewer.
- `git status --short` after push contains only the unrelated `.stale/` entry; repo control PASS.

REVIEW-0049 is therefore resolved. The governing publication task is no longer assigned to
Jr Dev - Hermes; next required actor is the Reviewer. Ticket acceptance is recorded under
REVIEW-0050_BYB-001_ACCEPTED.md.
