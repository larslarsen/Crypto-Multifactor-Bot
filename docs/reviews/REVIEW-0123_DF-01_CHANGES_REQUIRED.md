# REVIEW-0123 — DF-01 CHANGES REQUIRED

**Reviewed commit:** 919797a35fca91a2eb9006b590278bb7dbe4fdd5
**Decision:** CHANGES_REQUIRED
**Date:** 2026-07-21

## Findings (exact)
1. **E01 mis-described.** DF-01 in `research/sprint_002/06_DATA_FEASIBILITY_BACKLOG.csv`
   defines the P0 historical circulating/max/FDV supply question, lists candidate primary
   sources including **Coin Metrics (ATLAS)**, records point-in-time/vintage risks and the
   contemporaneous-value audit test. It does **NOT** establish the Coin Metrics *Community*
   role or authority. The current register row wrongly attributes the Community
   REFERENCE_METADATA / EXPLORATORY_PHASE2 role to E01.
2. **E03 / G05 over-claim.** E03 (`research/sprint_003/02_SOURCE_OBJECT_INVENTORY.csv`)
   records request URLs, retrieval/status facts, and observations. E08/E09 record the
   accepted hashes. The current wording implies E03 itself contains hashes for every
   timeseries request, which is not the case (some rows have empty sha256).
3. **E07 mis-attribution.** E07 (`research/sprint_003/13_RESEARCH_LEAD_DECISIONS.md`)
   records, via the AUD-003 acceptance, that Coin Metrics Community is
   `CONDITIONAL — EXPLORATORY_PHASE2` and DIL-01 remains deferred. The current wording
   attributes the new DF-01 NO_PRIMARY_PIT_SUPPLY_AUTHORITY decision to that prior record.
4. **G04 over-claims impossibility.** Past-value reproducibility is *not demonstrated* from
   the repository-retained evidence; it should not be claimed universally impossible.
5. **G08 over-claims provider absence.** Max/future-unissued supply is absent from the
   retained DF-01 evidence; the provider should not be claimed to universally lack it.
6. **Priority.** DF-01 should be P0 (it is the P0 historical supply question), not P1.

## Authorized corrections (COMMIT 2)
- Set DF-01 priority P0 in ticket and backlog.
- Correct E01: defines the P0 question; lists ATLAS among candidates; records PIT/vintage
  risks + contemporaneous-value test; does NOT establish Community role/authority.
- Correct E03/G05: E03 records URLs/retrieval/status/observations; E08/E09 record accepted
  hashes; do not claim E03 has a hash for every timeseries request.
- Correct E07 to exactly the AUD-003 acceptance: Coin Metrics Community is
  CONDITIONAL — EXPLORATORY_PHASE2 and DIL-01 remains deferred; do not attribute the DF-01
  decision to that prior record.
- Qualify G04: not demonstrated from retained evidence; not universally impossible.
- Qualify G08: absent from retained DF-01 evidence; not claimed universally lacking.
- Preserve all eight gate results, all blocking, NO_PRIMARY_PIT_SUPPLY_AUTHORITY, the
  conditional role, and downstream blockers (SIZE-01, DIL-01, supply-dependent NET-01).
