# Code review checklist

## Scope
- [ ] One ticket only.
- [ ] No opportunistic framework or architecture expansion.

## Data integrity
- [ ] Event time and availability time are distinct where needed.
- [ ] IDs and hashes are deterministic.
- [ ] Writes are atomic and immutable.
- [ ] Missingness and quarantine are explicit.
- [ ] Retried execution is idempotent.

## Research integrity
- [ ] No future information enters features, thresholds, universe, or costs.
- [ ] Labels remain separated.
- [ ] Complete prediction coverage is retained.
- [ ] Costs and no-trade states are not filtered from evaluation.

## Boundaries
- [ ] Imports conform to the layer matrix.
- [ ] Research contains no network or broker access.
- [ ] Execution consumes promoted manifests only.

## Operations
- [ ] Failure is recorded and fails closed.
- [ ] Memory and thread use are bounded.
- [ ] Logs avoid credentials and raw response bodies containing secrets.
