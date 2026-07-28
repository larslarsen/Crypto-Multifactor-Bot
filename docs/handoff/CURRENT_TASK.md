# CURRENT_TASK

Ticket: DATA-009
State: AWAITING_REVIEW
Next required actor: Sol 5.6 High
Final reviewer: Sol 5.6 High
Next ticket authorized: NONE

## Summary

Sr Dev corrected bitmex_funding.py and backfill_bitmex_funding.py with /instrument/all
endpoint discovery, 120 req/min polite budget, resolve_code_commit(), 429 retry tracking,
and full-merge publication. Jr Dev ran the acceptance suite: ruff clean, control plane PASS,
8/9 funding tests pass (1 failure is disk quota on /tmp, not code). Real report at
research/sprint_004/39_BITMEX_FULL_BACKFILL.json (real_asof, 6943 records, 2016-2026).
AWAITING_REVIEW.

## Governing documents

- tickets/DATA-009.md

## Authorization

Sol 5.6 High reviews and accepts/rejects. No further Jr work until authorized.
