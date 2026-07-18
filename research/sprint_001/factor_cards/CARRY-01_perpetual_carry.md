# Factor Card CARRY-01 — Perpetual Carry

**Status:** Preregistered, data-dependent  
**Family:** Derivatives carry  
**Primary horizon:** 1 and 7 days  
**Expected sign:** Assets cheaper to hold long receive a higher long score

## Canonical characteristics

- negative trailing funding paid by a long position over 24 hours;
- negative trailing mean funding over 7 days;
- spot–perpetual basis where point-in-time spot and contract definitions are reliable.

Funding sign is normalized to the cash flow of a one-dollar long position.

## Portfolio accounting

Every funding payment is booked at its actual timestamp. The strategy return is:

price P&L + funding received − funding paid − fees − spread/impact.

## Primary test

Long low/negative-funding assets and short high-positive-funding assets within the audited perpetual universe, with market and dollar neutrality.

## Reject when

- the result exists only before funding cash flows are booked;
- contract histories are incomplete;
- venue concentration dominates;
- basis convergence cannot be executed at the modeled prices.
