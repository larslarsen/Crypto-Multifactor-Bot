# REVIEW-0251 - ARCH-002 CONTINUE SOURCE

**Decision:** CONTINUE_SOURCE
**Reviewer:** Sol 5.6 High

The REVIEW-0250 fix records per-decision fingerprints in `PaperLoopPeriodLog`, but most
research builders discard those logs and serialize only `binding_evidence(...first
decision...)`. Their JSON artifacts still lose the remaining decision-time coverage.

Claude must continue immediately:

1. Add one shared serializer for the complete ordered per-decision binding evidence
   series, sourced from `PaperLoopResult.period_logs` where a loop ran.
2. Persist that complete series in all 11 entrypoint artifacts, every grid cell, and
   every train/test fold. A first-decision summary alone is insufficient.
3. Keep a compact top-level summary if useful, but never discard the complete series.
4. Strengthen tests to reject artifacts/cells whose serialized decision evidence count
   differs from their decision count or whose timestamps differ from executed periods.
5. Inspect all 11 builders once, finish the full cross-cutting edit, and self-review it
   before returning. No other ARCH-002 source change is requested.

No Git or tests were run by the reviewer.
