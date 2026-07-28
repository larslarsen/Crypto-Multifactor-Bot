# REVIEW-0249 - ARCH-002 REWORK AUTHORIZED

**Ticket:** ARCH-002 - UniverseBinding Contract
**Decision:** ADR-0014 ACCEPTED; ARCH-002 REWORK AUTHORIZED
**Reviewer:** Lead Quantitative Finance Researcher/Engineer
**Date:** 2026-07-27

## Selection

ARCH-002 is the next ticket. It is P0 and ADR-0014 explicitly places fail-closed
survivorship binding ahead of further raw-universe expansion or experiment work.
UNIVERSE-006 and DATA-011 are now available for the real composite binding path.

## Required rework

Complete REVIEW-0217 in one uninterrupted source pass:

1. Define membership as the declared quality-bar panel minus assets dead at decision
   time, never as dead-list membership.
2. Use name-safe CMC mapping; emit only valid paper/instrument keys and never raw
   `cmc_*` identities.
3. Fail closed on missing catalog inputs, empty panel, empty mapped intersection, or
   unavailable as-of coverage.
4. Bind and fingerprint exact universe and bar-panel dataset identities, policy version,
   decision time, and coverage.
5. Preserve the accepted protocol, paper-loop wiring, invalidation helper, and
   `TYPE_CHECKING` circular-import fix.
6. Prove the real catalog path against accepted UNIVERSE-006 and DATA-011: liquid panel
   names remain present, known dead names leave after death, recent membership is
   non-empty, and no static-map fallback exists.
7. Inspect every affected paper/experiment entrypoint and finish all source corrections
   before returning. Do not split this into intermediate reviewer rounds.

## Routing

Use **Sr Dev - Claude Opus 5** for the full bounded source implementation and its own
final source review, maximizing the available Claude development window. After Claude
reports the entire source delta clean, route once to Jr Dev - Hermes for integration,
tests, records, Git, and publication. Reviewer rereview occurs only after that complete
candidate.

## Constraints

No new factor research, EXP-009 execution, DEX-003, UNIVERSE-005, DATA-009, promotion,
or LIVE work is authorized.

## Next

- **Next required actor:** Sr Dev - Claude Opus 5
- **Next ticket authorized:** ARCH-002 only
