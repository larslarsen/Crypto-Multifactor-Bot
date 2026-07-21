# RAW-002 - SR SOURCE TRAVERSAL CORRECTION TASK

**Ticket:** `tickets/RAW-002.md`
**Actor:** Sr Dev - Sandbox
**Status:** AUTHORIZED AFTER CONTROL PUBLICATION - SOURCE ONLY
**Next ticket:** `NONE`

## Assignment

Correct only traversal detection in `assert_lexical_under_root`.

## Required Behavior

- Detect and reject `.` or `..` in the candidate's lexical components before `normpath` can erase
  them.
- Continue requiring an absolute path lexically contained by the resolved root.
- Do not resolve or follow candidate path components.
- Preserve all other RAW-002 source behavior unchanged.

## Scope

Local production-source correction only. Reviewer inspects the local source drop; Jr Dev - Hermes
owns later tests, integration, records, commit, and push.

## Completion Condition

Complete the minimal local source correction for reviewer inspection.
