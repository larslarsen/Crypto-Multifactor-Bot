# Deferred-Factor Data Gates

## Principle

DIL-01 and NET-01 remain deferred. This addendum makes readiness decisions measurable without
inventing thresholds before source behavior is audited. Data thresholds are frozen before
factor outcomes and may not be relaxed to improve results.

## Hard integrity gates

Every observation admitted to a primary experiment must satisfy all of these zero-tolerance
conditions:

- immutable source/vintage identity and content hash;
- event, publication/availability, and local acquisition times;
- no consumption before `availability_time`;
- versioned corrections with old values retained;
- unambiguous point-in-time asset, chain, contract, and unit mapping;
- explicit missing/unknown state rather than zero or hindsight reconstruction;
- reproducible as-of query and dataset lineage.

Failure is exclusion or quarantine, never a softer coverage score.

## Quantitative audit fields

Before unblocking either factor, an immutable audit reports by provider, metric, asset, and
calendar period:

- eligible asset-date coverage numerator/denominator;
- continuous-history length and longest gap;
- median, p95, and maximum availability lag;
- revision count/rate, revision magnitude, and vintage retention rate;
- mapping coverage and ambiguous mapping count;
- stale-value frequency and update cadence;
- cross-provider disagreement where an independent source exists;
- delisted/migrated/wrapped-asset coverage;
- selection differences between covered and uncovered assets.

## Threshold freeze

The data audit proposes numerical minimum coverage, maximum permitted lag/staleness, and
required history for the intended universe/horizon. The reviewer freezes or rejects those
thresholds before any factor-return result is computed. The gate record includes the
scientific estimand lost through exclusions and a power/selection assessment.

No generic percentage is adopted now: Sprint 003 did not establish an empirical distribution
from which a defensible universal cutoff could be selected.

## DIL-01 additions

The audit must separately cover circulating supply, max/FDV supply, announced schedules,
schedule revisions, actual unlock execution, burns, migrations, and redenominations. Each
unlock requires announced-at, known-from, revised-at, and executed-at semantics. "No unlock"
must be distinguishable from "unknown schedule."

## NET-01 additions

Each metric requires a versioned definition, chain/token mapping, spam/entity-adjustment
policy, finality rule, provider revision policy, and availability-time reconstruction.
Protocol fees, protocol revenue, tokenholder cash flow, emissions, and staking rewards remain
separate measures; gross fees are not labeled tokenholder yield.

## Unblocking decision

Passing a source gate makes a factor testable, not supported. Unblocking is an append-only
review event tied to an audit dataset ID and threshold configuration. DIL-01/NET-01 statuses
remain `DEFERRED`/`UNTESTED` until that event exists.
