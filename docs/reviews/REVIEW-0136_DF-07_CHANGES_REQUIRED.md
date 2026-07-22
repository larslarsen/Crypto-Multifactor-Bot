# REVIEW-0136 — DF-07 CHANGES REQUIRED

**Reviewed commit:** 9750a651a5a1368f4283e42b62a9fb29355a054e
**Decision:** CHANGES_REQUIRED
**Date:** 2026-07-22

## Attribution findings (exact)
1. **E02 over-claims observations.** The register role claims the NET-01 addendum records
   "bounded observations; coverage/depth limits; original API response bodies not retained."
   The addendum (NET-01 literature addendum) defines requirements/deferred status only — it does
   NOT record bounded observations, coverage/depth results, or raw-body retention. Correction:
   describe only that it defines NET-01 requirements and deferred status; no observation/coverage
   or retention claims.
2. **E04 mis-describes SRC-010.** The role claims "Records SRC-010 on-chain as '(not queried)...
   revisions/backfills none recorded'." The Sprint-003 object inventory has NO SRC-010 row. It
   only retains Coin Metrics observations and documents inventory limitations. Correction:
   describe only the retained Coin Metrics observations and inventory limitations; do not
   attribute SRC-010 content to E04.
3. **E09/E10 mislabeled metadata-only.** The roles call reconciliation/hash verification
   "bounded metadata" / "catalog/metadata objects" and state they do not retain raw bodies.
   REVIEW-0008 (lines 17-20) records that staged raw provider datasets (including Coin Metrics
   response objects) were NOT committed, but the staged evidence they reconcile/hash includes
   those raw provider datasets. Correction: state E09/E10 reconcile/hash the staged Sprint-003
   evidence INCLUDING Coin Metrics response objects; do not call them metadata-only, and cite
   REVIEW-0008 lines 17-20 for the fact that staged raw datasets were not committed.
4. **G06 should be FAIL_PARTIAL, not FAIL_UNKNOWN.** Request identities, staged-object hashes, and
   bounded observations exist; raw response bodies are not repository-retained and full PIT
   provenance is unavailable. Correction: G06 -> FAIL_PARTIAL with that exact framing.
5. **G03/G08 cite E04 incorrectly.** E04 is the Sprint-003 inventory (Coin Metrics only, no SRC-010
   row). Correction: remove E04 from G03 and G08 citations; use E03/E05/E06 for SRC-010 not
   queried, timestamp differences, revisions, and the absent known-block test.
6. **G05 cites E02 for coverage.** E02 defines requirements/deferred status only. Correction:
   correct G05 citations; do not attribute coverage findings to E02.

## Preserved
Final decision NO_POINT_IN_TIME_ON_CHAIN_OBSERVATION_AUTHORITY; all eight gates remain blocking.

## Scope of this commit
Governance only. Synthesis corrections applied in COMMIT 2.
