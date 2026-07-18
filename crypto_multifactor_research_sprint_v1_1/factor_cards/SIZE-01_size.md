# Factor Card SIZE-01 — Size

**Status:** Conditional on point-in-time supply audit  
**Family:** Asset scale  
**Primary horizon:** 7 days  
**Expected sign:** Smaller capitalization receives a higher score, based on published crypto factor evidence

## Canonical characteristic

`size = -log(point_in_time_market_cap)`

Market cap requires:

- historically valid circulating supply;
- audited price;
- explicit handling of token burns, unlocks, migrations, and wrapped duplicates;
- provider vintage or defensible publication lag.

## Controls

Liquidity and age are reported jointly. A small-asset premium that disappears under implementability constraints is not promoted.

## Reject when

Point-in-time supply cannot be reconstructed or the factor is entirely an illiquidity/microcap effect.
