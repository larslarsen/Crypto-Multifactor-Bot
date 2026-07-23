# ADR-001: Completed Bar Window Semantics
## Status: Accepted
## Decision: observation_eligible uses closed upper bound [valid_from, valid_to]
for market bars. Production bars set availability_time = period_end; making
the window inclusive at period_end allows completed bars to be selectable at
their availability time. reference_eligible stays half-open [valid_from, valid_to).
## Consequences: Completed bars are available immediately at availability_time.
Boundary case: t = period_end returns the bar. No impact on ref datasets.
