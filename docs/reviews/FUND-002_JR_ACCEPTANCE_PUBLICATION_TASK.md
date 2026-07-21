# FUND-002 - JR ACCEPTANCE PUBLICATION TASK

**Ticket:** `tickets/FUND-002.md`
**Actor:** Jr Dev - Hermes
**Status:** COMPLETED - ACCEPTANCE RECORDS AND PUBLICATION
**Next ticket:** `NONE`

## Exact Record Fixes

1. Set evidence row R05 sidecar ETag to `f00fbfdb979f43baa48fb461e04f22e1`.
2. Register `/tmp/fund_002_raw/docs/README_commit.json` with its exact GitHub API request, retrieval
   UTC, status, SHA-256, byte size, and external path, or remove the retained file/path claim and use
   only already registered pinned-URL evidence.
3. Register `/tmp/fund_002_raw/docs/LICENSE.headers` with exact metadata.
4. In the source note, label ETag `d6bc...` as the mutable `master` README response ETag. Use the
   pinned body URL/hash, not that mutable ETag, as pinned-content evidence.
5. Add the failed `FUND-002_JR_FINAL_EVIDENCE_INTEGRITY_TASK.md` status to the report's task history.
6. Update evidence-row counts after any added rows.

Do not change gate statuses, source conclusions, or `NO_IMPLEMENTATION_AUTHORITY`.

## Accepted-State Records

- Set FUND-002 ticket/report/README/backlog to `ACCEPTED - NO IMPLEMENTATION AUTHORITY`.
- Set handoff state to `ACCEPTED`, name Reviewer as next actor, and retain
  `Next ticket authorized: NONE`.
- Add REVIEW-0098 and this task to governing documents.
- Mark this task complete only after all records agree.

## Acceptance Command

Run `python3 scripts/check_repo_control.py` and record the literal PASS result. No pytest rerun is
required. Commit, push, return control to Reviewer, and stop. Do not begin another ticket.
