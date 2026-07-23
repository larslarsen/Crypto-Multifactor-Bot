# ADR-001: Completed Bar Window Semantics
## Status: Accepted
## Decision
Market-bar eligibility is dual-path:

- **latest_available:** availability-only — `availability_time <= t` and
  `period_start <= t`. No `period_end` upper bound. Selects the latest completed
  bar that is already available (production BAR-001 sets
  `availability_time = period_end`).
- **as_of:** `observation_eligible` with closed window
  `[period_start, period_end]` — `valid_from <= t <= valid_to` (open when
  `valid_to` is None), plus `availability_time <= t`. Answers "what was true
  at t" within the bar's period.

`reference_eligible` stays half-open `[valid_from, valid_to)`.

## Rationale
- `latest_available` = "latest available bar" for history walks and factor
  inputs; bars remain selectable after `period_end` once available.
- `as_of` = "what was true at t"; period membership uses the closed upper bound
  so a bar is selectable at `t = period_end` when that equals availability.

## Consequences
- Completed bars are available immediately at `availability_time`.
- Boundary case: `t = period_end` returns the bar via both paths.
- History walk (`availability_time - 1µs` rewind) can still select prior bars
  through `latest_available`.
- No impact on ref datasets.
