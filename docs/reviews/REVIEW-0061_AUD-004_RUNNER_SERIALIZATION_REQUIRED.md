# REVIEW-0061 - AUD-004 RUNNER SERIALIZATION REQUIRED

**Ticket:** AUD-004 - Native headerless support for the Binance archive precision comparator
**Status:** CHANGES_REQUIRED - CONTROL PUBLICATION, THEN SR SOURCE
**Next required actor:** Jr Dev - Hermes, then Sr Dev - Sandbox
**Next ticket authorized:** `NONE`
**Date:** 2026-07-20

## Decision

AUD-004 remains in progress. The five Sprint-003 errors are not an unrelated baseline failure.
Before AUD-004, the native headerless call failed and the runner serialized only failure text.
After AUD-004, the call succeeds and `precision_report` places the returned
`BinancePrecisionComparison` dataclass into deterministic output. Its float threshold fields then
reach `source_audit.serialization`, which correctly rejects floats.

## Required Source Correction

Adapt the successful native comparison at the Sprint-003 runner boundary in
`scripts/audit/run_sprint003_audit.py`. Convert the dataclass to an explicit deterministic,
serializer-supported value and represent its two threshold rates losslessly without floats.

Do not weaken the global no-float serializer, change unrelated source-audit model contracts, hide a
successful native result, or restore the obsolete headerless failure path. Preserve paths, schema
diffs, distributions, counts, rationale, and threshold values in the emitted report.

The exact local source task is `docs/reviews/AUD-004_SR_RUNNER_SOURCE_TASK.md`.

## Remaining Jr Evidence

After reviewer source approval, Jr Dev - Hermes must integrate the runner correction, complete the
full suite, add the missing archive-B malformed/sample assertions, correct contradictory state and
gate records, commit, and push.
