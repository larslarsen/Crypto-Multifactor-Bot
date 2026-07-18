# Literature Synthesis

## 1. Evidence hierarchy

The literature is divided into:

- **Tier A:** peer-reviewed, directly relevant crypto asset-pricing or market-microstructure evidence;
- **Tier B:** peer-reviewed general asset-pricing methodology;
- **Tier C:** crypto working papers that motivate tests but do not establish production priors;
- **Tier D:** practitioner or single-study ideas used only for exploratory context.

The new initiative is anchored in Tier A/B. Tier C creates optional hypotheses.

## 2. Direct crypto evidence

### Cross-sectional factors

Liu, Tsyvinski, and Wu report that crypto market, size, and momentum factors capture much of the cross-section in their sample. This justifies a direct replication of size and momentum, not the assumption that the factors remain profitable in a newer, more institutional, costed universe.

### Time-series predictability and network effects

Liu and Tsyvinski find crypto-specific momentum and investor-attention/network relationships. This supports momentum and network-adoption hypotheses, but their principal asset sample and question differ from a broad live cross-sectional portfolio.

### Venue segmentation

Makarov and Schoar document large, recurring cross-exchange price differences and market segmentation. This means venue is an economic dimension, not a harmless data-source label.

Hautsch and coauthors link settlement latency/default risk to cross-exchange differences. The implication is that apparent arbitrage or “cleaner” venue prices may carry transfer and counterparty risk.

### Volume reliability

Cong and coauthors document extensive wash trading on many unregulated exchanges. Reported volume therefore requires source reliability controls before it determines universe membership, features, or capacity.

## 3. Candidate crypto evidence

### Staking and carry

Recent staking research provides a mechanism and empirical motivation for crypto carry. It does not prove that perpetual funding, staking yield, and basis are interchangeable. Each cash flow receives a separate factor definition.

### On-chain cash flows

Working-paper evidence suggests protocol revenues and related valuation ratios may matter cross-sectionally. Because token rights, protocol accounting, and historical publication times are difficult, this remains Phase 2.

### Broader risk premia

Working papers report liquidity, reversal, volatility, and other crypto characteristics. These are useful candidates but require independent reconstruction under the new universe and costs.

## 4. General asset-pricing methodology

### Machine learning

Gu, Kelly, and Xiu show that nonlinear models can add value in high-dimensional expected-return prediction. Their work also demonstrates the need for genuine out-of-sample evaluation and strong baselines. It does not imply that XGBoost is automatically appropriate for this crypto dataset.

### Factor proliferation

Harvey, Liu, and Zhu show why conventional significance is insufficient after many factor searches and recommend a much higher hurdle for new discoveries.

Hou, Xue, and Zhang find that many published equity anomalies fail stricter replication and microcap controls. The crypto analogy is direct: tiny, illiquid assets can manufacture apparent factor returns.

### Backtest overfitting

Bailey and coauthors formalize the probability of backtest overfitting after strategy selection. The legacy repository's many indicator, regime, and slicing experiments make an experiment census and future holdout mandatory.

### Trading costs

Novy-Marx and Velikov show that anomaly economics can change materially after costs and that turnover mitigation matters. Crypto factors must be evaluated with spread, impact, funding, and shortability before promotion.

### Portfolio estimation

DeMiguel, Garlappi, and Uppal show that optimized portfolios often fail to beat naive equal weight out of sample because of estimation error. Equal weight is therefore a required baseline.

Ledoit–Wolf shrinkage supplies a conservative covariance baseline when the asset dimension is large relative to the sample.

## 5. Design decisions implied by the literature

1. Start with market, momentum, and conditional size.
2. Add reversal, defensive, liquidity, and carry as preregistered candidate families.
3. Treat venue, volume reliability, settlement, and shortability as first-class data.
4. Keep on-chain and staking extensions separate until point-in-time integrity is proven.
5. Test transparent sorts before ML.
6. Use equal-weight and regularized baselines.
7. model costs before declaring alpha.
8. count all trials and apply multiple-testing controls.
9. require a prospective holdout.
10. avoid microcap-driven conclusions.

## 6. Claims the literature does not justify

The reviewed literature does not justify:

- a promised Sharpe range;
- a claim that 113 technical features are diversified factors;
- a conclusion that volume bars are an edge based on unmatched accuracy;
- using current survivors historically;
- treating free-exchange volume as ground truth;
- expecting regime-specific models to work with small samples;
- preferring ML before simple factor portfolios are tested.

See `09_LITERATURE_LEDGER.csv` for the source-level extraction.
