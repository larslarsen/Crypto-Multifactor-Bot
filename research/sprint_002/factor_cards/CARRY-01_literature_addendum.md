# Literature Addendum — CARRY-01 (Perpetual Carry)

**Card:** CARRY-01 (Sprint 001, now split into mechanisms)
**Sprint:** 002 refresh
**Status:** retained; split into futures-basis / funding / staking / emissions legs

## What Sprint 1 already specified

Perpetual carry via negative trailing funding, basis where reliable, with funding booked at
actual timestamps; long low-funding / short high-funding; reject if result exists only before
funding cash flows are booked.

## What the new literature changes

- LIT-025 (Schmeling/Schrimpf/Todorov 2026, Management Science): peer-reviewed crypto carry
  on futures basis; large monthly premia that collapse in stress.
- LIT-035 (Scharnowski & Jahanshahloo 2025, JFM): liquid-staking basis determinants.
- LIT-037 (Zhivkov 2026, Mathematics): funding-rate market is two-tier (CEX-dominated); most
  arbitrage spreads vanish after costs.
- LIT-018 (Cong/He/Tang, NBER w33640, 2025): staking links to crypto carry premia.

## What remains unchanged

Funding must be booked at actual timestamps; contract histories must be complete; basis
convergence must be executable. These are preserved.

## Additional diagnostics (new)

Report each mechanism separately with its own data and test; do not collapse into one yield
factor without spanning evidence (RD-04). For funding, report CEX-vs-DEX fragmentation and
post-cost profitability (LIT-037).

## New data requirements

Point-in-time funding rates + exact cash-flow times (DF-03); fixed-expiry futures basis
(DF-04); staking-reward histories and eligibility (DF-05); shortability/margin terms (DF-06).

## Why it remains untested (in this project)

Literature refresh only. CARRY-01 / H-004 stays `DEFERRED` until the derivatives data
foundation (DF-03..DF-06) is built and audited.
