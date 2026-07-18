# Research Charter

## 1. Mandate

Build and independently validate an implementable cryptocurrency multifactor model that ranks a point-in-time investable universe by expected **net** return.

The initiative is greenfield. Existing code, features, thresholds, labels, and model weights do not receive grandfathered status.

## 2. Primary research question

At a decision time \(t\), which eligible cryptoassets have higher or lower expected returns over a prespecified holding horizon, after accounting for:

- common crypto-market exposure;
- transaction costs and market impact;
- perpetual funding and borrow/short constraints;
- turnover and capacity;
- data publication delays;
- delistings and venue availability?

## 3. Unit of analysis

The primary object is a date–asset panel:

\[
(i,t) \rightarrow \left(x_{i,t}, r_{i,t\rightarrow t+h}^{net}\right)
\]

where every feature has an explicit availability time and every return maps to a realizable portfolio action.

## 4. Primary strategy families

Two implementations are researched in parallel:

### A. Long-only ranking

Long the highest-scoring eligible assets; benchmark against an equal-weight eligible-universe portfolio and the broad crypto market.

### B. Market-neutral ranking

Long the highest-scoring and short the lowest-scoring assets only where point-in-time perpetual availability and funding are known. Target low market beta and dollar neutrality.

Neither implementation is presumed superior.

## 5. Horizons

- **Primary:** seven-calendar-day forward return, weekly rebalance.
- **Secondary:** one-calendar-day forward return, daily rebalance.
- Longer or intraday horizons are exploratory until the primary baselines are complete.

Weekly research is scheduled on a fixed UTC decision time. Daily research uses one fixed UTC decision time. No favorable weekday is selected from results.

## 6. Preregistered factor hypotheses

### H1 — Medium-term momentum

Risk-adjusted returns over medium lookbacks, excluding the most recent reversal window, contain positive cross-sectional information.

Canonical candidates: 30–7 and 90–7 calendar-day returns.

### H2 — Short-term reversal

Extreme one- to three-day returns partially reverse, especially when accompanied by temporary volume or price-impact shocks.

### H3 — Defensive risk

Lower realized volatility, downside risk, beta, or idiosyncratic volatility improves risk-adjusted outcomes and may predict the cross-section.

### H4 — Perpetual carry

Cross-sectional differences in funding and basis contain implementable carry information after the actual funding cash flows and execution costs are included.

### H5 — Liquidity

Liquidity has two separate roles:

1. **tradability constraint**, which is mandatory;
2. **candidate alpha characteristic**, which must be tested independently.

The two roles must never be conflated.

### H6 — Size

Point-in-time market capitalization may explain cross-sectional returns. It is tested only if circulating supply and market-cap histories pass a point-in-time audit.

### H7 — Network activity and protocol economics

Lagged network adoption, activity, and protocol cash-flow measures may add information beyond price-based factors. These enter Phase 2 only after publication-time integrity is demonstrated.

### H8 — Market state is primarily a risk control

Market regimes may change gross exposure, risk targets, and cost tolerance. They are not initially permitted to select among a large zoo of indicator-specific models.

## 7. Nulls and falsification

Every factor starts with a null of no incremental net value.

A factor is rejected or archived when it:

- lacks monotonic cross-sectional behavior;
- depends on one venue, one era, or a handful of assets;
- disappears after point-in-time controls;
- fails after conservative costs;
- has no incremental contribution beyond simpler factors;
- relies on an unavailable or non-auditable input;
- requires repeated threshold search to look favorable.

A negative result is a valid output and is recorded in the graveyard.

## 8. Baseline ladder

A complex method may advance only after beating all preceding baselines:

1. eligible-universe equal weight;
2. single-factor quantile portfolios;
3. equal-weight standardized factor composite;
4. volatility-scaled equal-factor composite;
5. regularized linear cross-sectional model;
6. shallow nonlinear model;
7. more complex ML only with clear net economic improvement.

## 9. Promotion standard

A factor or model is not called validated until it has:

- a written economic rationale;
- point-in-time data and universe membership;
- predefined signal and horizon;
- a conservative costed portfolio;
- nested chronological evaluation;
- dependence-aware inference;
- multiple-testing accounting;
- an untouched prospective holdout;
- a reproducible experiment bundle.

No target Sharpe ratio is stated in advance.

## 10. Scope boundaries

### In scope now

- liquid centralized-exchange spot and perpetual assets;
- daily and weekly cross-sectional models;
- momentum, reversal, defensive, liquidity, carry, and conditional size;
- transparent portfolios and regularized models;
- volume-bar replication as a separate representation experiment.

### Deferred

- DEX tokens;
- high-frequency order-book models;
- online reinforcement learning;
- automated real-money execution;
- leverage optimization;
- protocol-specific on-chain models;
- architecture optimized around a particular ML library.

## 11. Research governance

- Every experiment receives an ID before execution.
- Exploratory and confirmatory work are labeled separately.
- All tried variants count toward the researcher's degrees of freedom.
- Results are appended; failed rows are not deleted.
- Parameter changes create a new experiment ID.
- The final prospective holdout is opened once per declared research version.

## Post-freeze evidence treatment

Legacy commits after the initial freeze may be reviewed as evidence, but they do not reopen preregistered hypotheses or promotion rules. Commits `581aed2` and `fb737ae` are classified as contaminated legacy research because their design and artifacts were produced before the clean replication protocol and because the evaluator does not satisfy causal fold-local validation.
