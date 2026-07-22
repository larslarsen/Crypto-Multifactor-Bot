# REVIEW-0133 — DF-03 CHANGES REQUIRED

**Reviewed commit:** 6d28d91df9bd7627022b364170e76feca8dfa61a
**Decision:** CHANGES_REQUIRED
**Date:** 2026-07-22

## Attribution findings (exact)
1. **E01 mis-attributed.** The register role attributes position-dependent / common-numeraire
   requirements to Sprint-002. The exact Sprint-002 record (`research/sprint_002/06_DATA_FEASIBILITY_BACKLOG.csv`,
   DF-03 row) is: historical perpetual funding rates and exact cash-flow times; PIT risk = discrete
   accrual times and contract specifications in force; required test = replay a known funding
   payment against the contract formula at that timestamp. It does NOT attribute position-dependent
   or common-numeraire requirements to E01.
2. **E02 mis-states RD-02.** The register role claims RD-02 recorded FUND-001/002/003 decisions and
   proposed a normalizer/CARRY path. The exact Sprint-003 RD-02 (`research/sprint_003/08_RESEARCH_DATA_DECISIONS.csv`)
   is: Binance monthly funding archive acquired with `last_funding_rate` and observed 8h interval;
   OKX/Bybit funding history reachable as incremental evidence; actual funding settlements determine
   cashflows; next action = capture funding interval and formula type per timestamp, never project
   current rules backward. RD-02 predates and does NOT record FUND-001/002/003 decisions or grant
   implementation authority.
3. **E07 field mislabel.** The register role labels the Binance field as `fundingRate`. The archive
   fields are `calc_time`, `funding_interval_hours`, and `last_funding_rate`. `last_funding_rate`
   must not be relabeled as `fundingRate` (the latter is the REST field it is matched against).
4. **G07 citations wrong.** Current matrix cites E06/E10 (tickets) and E09/E13 (acceptances) for the
   licensing gate. Correct: E07/E08 (Binance report + matrix) and E11/E12 (OKX report + matrix);
   tickets/acceptance records may establish final status but are NOT the primary legal-semantics
   evidence.
5. **G08 citations wrong.** Current matrix cites E07/E11 (rate events) + E14/E15/E16 (FX). Correct:
   E03/E04/E05 (FUND-001 funding-event vs position-dependent realized-cashflow separation), E07/E11
   (provider funding-rate-event evidence), E14/E15/E16 (FX-003 no-primary-authority boundary).

## Scope of this commit
Governance only. No synthesis corrections are applied here. Gate results, decision, P0, gate role,
and accepted FUND/FX boundaries are unchanged.
