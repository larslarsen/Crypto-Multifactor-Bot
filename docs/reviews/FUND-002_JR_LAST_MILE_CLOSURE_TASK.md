# FUND-002 - JR LAST-MILE CLOSURE TASK

**Ticket:** `tickets/FUND-002.md`
**Actor:** Jr Dev - Hermes
**Status:** COMPLETED - MECHANICAL CLOSURE
**Next ticket:** `NONE`

## Scope

Do not change gate statuses or `NO_IMPLEMENTATION_AUTHORITY`. Make only the exact record fixes below.
Network access is limited to response-header captures for the correct USD-M and retained legacy-doc
requests if those headers are not already staged.

## Exact Fixes

1. Report header:
   - add `**Ticket:** FUND-002`;
   - set next actor to Reviewer;
   - state `four FAIL, two PARTIAL, one PASS, and one BLOCKED`.
2. Register:
   - set BTCUSDT February sidecar ETag to `f00fbfdb979f43baa48fb461e04f22e1`;
   - set ETHUSDT January sidecar ETag to `412152171a26fca9add06dc3a24e1e73`;
   - set funding-listing and updates-listing HTTP statuses to 404;
   - add full rows for `funding_listing.headers` and `updates.headers`;
   - add full response-header rows for the correct USD-M docs attempt and retained legacy redirect;
   - add a separate mutable README body row if the mutable body remains staged;
   - update final evidence-row counts everywhere.
3. Source note:
   - cite pinned README commit/path as authority;
   - record mutable README separately;
   - record LICENSE 404 separately from the README MIT statement;
   - record both listing requests as 404;
   - record the correct USD-M docs empty-body attempt and legacy spot redirect as non-qualifying.
4. Mark the prior verifiable-closure task `FAILED - REVIEW-0097` and this task complete only after
   validation.

Every new row requires exact URL, retrieval UTC, HTTP status, SHA-256, nonnegative byte size, and an
existing external path. Empty bodies use the SHA-256 of empty bytes and size 0.

## Mechanical Validation

Run the same CSV validator required by REVIEW-0096 against the final register. Record its literal PASS
line and exact row count.

Run this scan over only the report, evidence register, and Binance source note:

`rg -n 'Obtain или|conflicts with accepted REF-001|14 rows|Four gates fail, two are partial,$|Next required actor:\*\* Jr Dev' docs/reviews/FUND-002_SOURCE_SEMANTICS_REPORT.md research/fund_002/EVIDENCE_REGISTER.csv research/fund_002/sources/binance.md`

Required result: no output, exit status 1. Record exactly that result.

## Acceptance And Stop

- Set ticket, report, README, backlog, and handoff to `AWAITING_REVIEW`; name Reviewer as next actor;
  retain `Next ticket authorized: NONE`.
- Run `python3 scripts/check_repo_control.py` and record the literal PASS result.
- Commit, push, and stop. No pytest run is required. Do not start another ticket.
