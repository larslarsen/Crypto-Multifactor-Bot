# REVIEW-0250 - ARCH-002 CHANGES REQUIRED

**Decision:** CHANGES_REQUIRED
**Reviewer:** Sol 5.6 High
**Date:** 2026-07-27

## Finding

**High - run artifacts do not persist the complete binding fingerprint.**
`PaperPanelSurvivorshipBinding.binding_fingerprint(t)` correctly binds both dataset ids,
policy/code versions, decision time, and coverage counts, but production code never
calls it. `PaperLoopResult` records only four scalar identity fields, and 10 of the 11
paper/experiment JSON builders omit even those fields. The artifacts therefore cannot
prove which binding and as-of coverage controlled each decision, contrary to ARCH-002
and REVIEW-0249 item 4.

## Required correction

1. Record `binding_fingerprint(decision_time)` for every paper-loop decision in the
   immutable loop result/period evidence.
2. Serialize the binding identity and decision-time coverage evidence in all 11 affected
   paper/experiment artifacts, including grid cells and train/test folds.
3. Add regression coverage proving no affected artifact omits universe id, bar-panel id,
   policy version, code version, decision time, and coverage.
4. Claude must inspect all 11 output builders and finish this cross-cutting correction
   before returning once to Jr. No other source rework is requested.

The composite panel-minus-dead semantics, name-safe mapping, fail-closed behavior, real
catalog integration, and static-membership removal are otherwise approved.

No Git or tests were run during this targeted local review.

## Next

- **Next required actor:** Sr Dev - Claude Opus 5
- **Next ticket authorized:** ARCH-002 only
