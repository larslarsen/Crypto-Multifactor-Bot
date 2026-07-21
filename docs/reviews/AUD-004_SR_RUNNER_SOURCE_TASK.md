# AUD-004 - SR RUNNER SOURCE TASK

**Ticket:** `tickets/AUD-004.md`
**Actor:** Sr Dev - Sandbox
**Status:** AUTHORIZED AFTER CONTROL PUBLICATION - SOURCE ONLY
**Next ticket:** `NONE`

## Assignment

Correct successful native precision-result serialization in
`scripts/audit/run_sprint003_audit.py`.

## Required Behavior

- Convert `BinancePrecisionComparison` to a deterministic serializer-supported structure at the
  runner boundary.
- Convert `max_malformed_rate` and `max_ambiguous_rate` to lossless non-float representations
  accepted by the existing serializer.
- Preserve every other result field and successful native status.
- Keep `source_audit.serialization`, source-audit model contracts, and unrelated runner behavior
  unchanged.

## Scope

Local runner-source correction only. Reviewer inspects the local source drop; Jr Dev - Hermes owns
subsequent integration, tests, evidence, records, commit, and push.

## Completion Condition

Complete the minimal local runner-source correction for reviewer inspection.
