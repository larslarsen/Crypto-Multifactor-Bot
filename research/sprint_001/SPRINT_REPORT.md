# Sprint 1 Report

## Outcome

Sprint 1 established the scientific and governance foundation for a greenfield cryptocurrency multifactor initiative.

It did **not** produce backtest performance, because the raw datasets and generated result artifacts described by the legacy repository are excluded from the public repository. Treating undocumented local claims as audited results would repeat the original process failure.

## Completed

- reviewed the current public repository structure, research notes, feature contract, labels, splits, quality gate, manifest approach, and experiment history;
- separated repository-verified facts from author-claimed local data/results;
- identified critical defects in split purging, intrabar barrier resolution, and historical universe construction;
- rebuilt the literature basis around peer-reviewed crypto asset pricing, crypto market structure, replication, costs, and multiple testing;
- defined the research question as cross-sectional expected net return;
- preregistered momentum, reversal, defensive, carry, liquidity, conditional size, and network factor families;
- defined a point-in-time U50 universe and robustness universes;
- defined data, availability, symbol-master, and missingness contracts;
- defined nested validation, event-time purging, dependence-aware inference, and multiple-testing rules;
- established equal-weight, equal-factor, volatility-scaled, linear, and nonlinear model ladders;
- created a matched replication protocol for volume/information bars;
- created a prospective sealed-holdout rule;
- produced an architecture handoff that specifies required interfaces without prematurely choosing implementation technology.

## Most important audit findings

1. The legacy walk-forward “purge” does not remove overlapping earlier labels at partition boundaries.
2. Triple-barrier labels give profit-barrier precedence when both barriers are touched within one OHLC bar.
3. The quality gate is based on whole-file/current-state information rather than historical as-of membership.
4. Missing optional features can be encoded as zero.
5. Raw data, model artifacts, and many experiment classes are not versioned publicly.
6. The documentation describes multiple competing “current” systems.
7. Prior experimentation is broad enough that historical data cannot be considered a pristine final holdout.
8. The volume-bar result is not yet an economically matched comparison.

## Binding research direction

The primary initiative is:

- liquid CEX spot/perpetual assets;
- weekly cross-sectional ranking, with daily secondary tests;
- a point-in-time U50 universe;
- transparent factors before ML;
- net return after fees, impact, funding, and short constraints;
- prospective confirmation after the research freeze.

DEX, high-frequency order flow, complex regime switching, and on-chain/protocol factors are deferred until their data contracts pass.

## Blocked work

The following require local metadata or raw data:

- exact dataset inventory and hashes;
- timestamp/schema audit;
- listing and delisting reconstruction;
- funding sign and cash-flow audit;
- market-cap and circulating-supply validation;
- factor return estimation;
- transaction-cost calibration;
- replication of reported legacy results;
- final architecture sizing and storage decisions.

## Architecture status

Architecture is intentionally **not** designed yet. The research interfaces are ready, but architecture depends on local facts such as data volume, update frequency, venue coverage, and point-in-time metadata availability.

## Next gate

Run the local data audit and export:

- dataset manifest;
- schema registry;
- instrument master;
- coverage by date;
- exceptions;
- experiment-file census;
- fee/funding source map.

Once those are available, Sprint 2 can execute the preregistered single-factor experiments and produce empirical factor reports.

## Post-sprint review — commits `581aed2` and `fb737ae`

The late commits were reviewed and incorporated into package v1.1.

They add useful versioned source and 27 information-bar model artifact sets, but they do not change the primary research direction. The implementation review found that:

- serving still produces time-bar inputs;
- the Paper #2 v2 evaluator fits one 80%-sample model and reuses it across nominal folds;
- information-bar thresholds depend on complete-sample volume;
- evaluator and artifact trainer use different feature-construction order;
- the alternate-venue treatment does not actually group bars on alternate-venue volume;
- headline accuracy excludes flat predictions and is not a costed portfolio outcome;
- at least one artifact uses only 496 training bars for a 113-feature, 200-tree model.

Accordingly, all new information-bar performance is classified as `CONTAMINATED_LEGACY_EVIDENCE`. The artifacts are preserved for forensics and regression fixtures but are not approved for serving or factor promotion.

See `15_POST_SPRINT_COMMIT_REVIEW.md` and the updated `08_VOLUME_BAR_REPLICATION_PROTOCOL.md`.
