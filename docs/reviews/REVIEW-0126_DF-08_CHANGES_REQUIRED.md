# REVIEW-0126 — DF-08 CHANGES REQUIRED

**Reviewed commit:** b73309aba26878a353f32f1a042dc3c814921507
**Decision:** CHANGES_REQUIRED
**Date:** 2026-07-21

## Findings (exact)
1. **E05 mis-described.** The exact Sprint-003 RD-06 record must be reflected:
   - RD-06 recorded partial listing/delivery feasibility.
   - Its next action proposed an instrument-master (launchTime/deliveryTime/state) plus
     last-trade polling.
   - RD-06 did not itself grant source or implementation authority.
   - Later accepted REF-002/REF-003 decisions block the Bybit-dependent path.
2. **E03 / G02 / G03 over-claim edges.** The retained evidence contains bounded
   earliest/latest timestamps within sampled/archive objects, NOT proven asset-lifetime
   first/last trades. BTCUSDU26 contains a scheduled future `deliveryTime`
   (1790323200000), which is not an observed completed delivery. Launch/scheduled-delivery
   metadata and bounded trade observations remain PASS_PARTIAL and blocking. Sample/archive
   edges must never be equated with lifecycle listing/delisting events.
3. **Accepted market-bar scope not registered.** BAR-001 accepted canonical-bar authority
   (tickets/BAR-001.md, REVIEW-0042_BAR-001_ACCEPTED.md) must be registered as preserved
   scope (E15/E16), with path/SHA-256/size, and DF-08 must state it does not downgrade
   accepted canonical-bar authority.
4. **Evidence counts** in report/source-note must move from 14 to 16, citing E15/E16 only
   for the preserved market-bar boundary.

## Authorized corrections (COMMIT 2)
- Correct E05 to the exact RD-06 wording above.
- Correct E03 and all G02/G03 wording: bounded sample/archive timestamps not proven
  asset-lifetime edges; BTCUSDU26 scheduled future delivery not a completed delivery;
  PASS_PARTIAL/blocking preserved; never equate edges with lifecycle events.
- Register E15 tickets/BAR-001.md and E16 REVIEW-0042_BAR-001_ACCEPTED.md (path/sha/size);
  state DF-08 does not downgrade accepted canonical-bar authority.
- Update report/source-note counts 14 → 16; cite E15/E16 only for the preserved market-bar
  boundary.
- Preserve exact matrix statuses (G01 PASS/No; G02 PASS_PARTIAL/Yes; G03 PASS_PARTIAL/Yes;
  G04 FAIL_UNKNOWN/Yes; G05 FAIL_UNKNOWN/Yes; G06 FAIL_PARTIAL/Yes; G07 FAIL_UNKNOWN/Yes;
  G08 FAIL_UNKNOWN/Yes), NO_SURVIVORSHIP_FREE_UNIVERSE_AUTHORITY, P0, and
  BLOCKING_FOR_SURVIVORSHIP_FREE_UNIVERSE.
