# REVIEW-0129 — DF-02 CHANGES REQUIRED

**Reviewed commit:** 1c545797a75bc7d5bddaccfa39a3b5fbfcba1a7a
**Decision:** CHANGES_REQUIRED
**Date:** 2026-07-21

## Attribution findings (exact)
1. **E03 mis-attributed.** `02_SOURCE_OBJECT_INVENTORY.csv` records Tokenomist's TLS error
   (TLSV1_UNRECOGNIZED_NAME), Messari's 404/429 no-key gap, and the old DefiLlama SDK path
   returning 404. It does NOT record the DefiLlama emissions HTTP 402 response (that is in
   `sources/defillama.md`, E12), and it does NOT establish retained adapter artifacts (the
   old SDK path is `INVALID_NONQUALIFYING`).
2. **E04 over-claimed.** `03_SCHEMA_AND_SEMANTICS_AUDIT.csv` records Tokenomist's expected
   schema as unconfirmed, vintage preservation as unknown (CANNOT CONFIRM vintage preservation),
   and on-chain vesting as required but unqueried. It must not describe observed on-chain
   execution fields (the on-chain row is `not queried`).
3. **E10 mis-attributed.** `13_RESEARCH_LEAD_DECISIONS.md` carries the Research Lead's
   per-provider decisions, not the source-register roles. Correct to exactly: DefiLlama =
   CONDITIONAL - EXPLORATORY_PHASE2 (emissions access not established as free); Tokenomist /
   Messari = DEFER pending authorized access or vendor trial; DIL-01 remains deferred. Do not
   attribute the separate source-register roles (Tokenomist DEFERRED, Messari CONDITIONAL/
   EXPLORATORY_PHASE2, DefiLlama unlock adapters CONDITIONAL/REFERENCE_METADATA, from E02) to E10.
4. **Matrix citations wrong.**
   - G01 must cite: E03 for Tokenomist/Messari/old-SDK access facts; E11 for Tokenomist/Messari
     details; E12 for DefiLlama HTTP 402; E07 for trial prerequisites.
   - G06 must cite E12/E13 for adapter artifacts and E11 for the partial bridge; do NOT cite E03
     as retained adapter evidence.
   - G07 must cite E07 vendor requirements plus E11 licensing warning; do NOT cite E10 as
     licensing evidence.
5. Report and source note repeat the same attribution errors and must be corrected consistently.

## Authorized corrections (COMMIT 2)
- Correct E03, E04, E10, and E02 (preserve source-specific roles) as above.
- Correct matrix G01/G06/G07 evidence citations as above.
- Apply the same attribution distinctions in the report and source note.
- Preserve all eight blocking gate results, NO_POINT_IN_TIME_UNLOCK_AUTHORITY, P0,
  BLOCKING_FOR_DILUTION_UNLOCK, downstream blockers, and no-authority scope.
