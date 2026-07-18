# Factor Card LIQ-01 — Liquidity

**Status:** Preregistered with role separation  
**Family:** Trading frictions  
**Primary horizon:** 7 days

## Mandatory tradability measures

- trailing median daily quote volume;
- valid-day fraction;
- spread proxy or observed spread;
- Amihud-style `abs(return) / quote_volume`;
- zero-return frequency;
- venue breadth.

These determine eligibility, costs, and capacity.

## Candidate alpha score

The alpha hypothesis is tested separately using lagged illiquidity measures. The sign is not hard-coded as a production belief: an illiquidity premium may exist gross, while implementation costs can reverse it net.

## Required reports

- gross factor return;
- observed/modeled cost;
- net factor return;
- capacity curve;
- results by liquidity tier;
- correlation with size.

## Reject as alpha when

Net returns are nonpositive or the signal is merely a proxy for tiny assets. Tradability measures remain mandatory even if alpha is rejected.
