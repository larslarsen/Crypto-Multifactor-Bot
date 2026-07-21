# AUD-005 - SR SOURCE TYPE CORRECTION TASK

**Ticket:** `tickets/AUD-005.md`
**Actor:** Sr Dev - Sandbox
**Status:** COMPLETED - SOURCE APPROVED BY REVIEW-0068
**Next ticket:** `NONE`

## Assignment

Correct only the `comparable_dimensions` input contract in `src/source_audit/bars.py`.

## Required Behavior

- Type the input as a collection of strings so `set[str]`, list, and tuple callers are valid.
- Reject a scalar string or bytes value as the collection.
- Reject any non-string collection member without converting it.
- Retain deterministic canonical ordering and existing rejection of empty, unknown, and duplicate
  dimensions.
- Keep all comparison, model, runner, and serialization behavior unchanged.

## Scope

Local production-source correction only. Reviewer inspects the local source drop; Jr Dev - Hermes
owns later tests, integration, records, commit, and push.

## Completion Condition

Complete the minimal local source correction for reviewer inspection.
