# 01 — Literature Refresh 2025–2026

**Sprint:** 002
**Research cutoff:** 2026-07-18
**Sources added:** LIT-024 … LIT-037 (14 verified)

This document summarizes the 2025–2026 evidence refresh. It is a research-design note, not
an empirical result. No factor is claimed validated. Every source was verified against its
primary page; the machine-readable ledger is `02_LITERATURE_LEDGER.csv`.

## Themes and what changed

### Momentum (Tier A reinforcement, later challengers)

- **CTREND (LIT-024, Fieberg et al. 2025, JFQA).** A price-and-volume trend factor that
  aggregates information across horizons and is not subsumed by known factors; survives
  transaction costs and persists in large/liquid coins. This is the canonical "complex
  price-volume combination" the roadmap should treat as a *later challenger* after simple
  momentum is frozen.
- **Risk-managed momentum (LIT-026, Yang 2025, FRL; LIT-027, Grobys et al. 2025, FMPM).**
  Volatility scaling raises Sharpe in crypto, but the two papers disagree on crash risk:
  Yang finds crypto lacks extended momentum crashes (gain comes from enhanced returns),
  while Grobys et al. document severe crashes in large-cap equal-weighted momentum and
  endorse volatility management for crash mitigation. **Decision:** report raw vs
  volatility-managed exposure separately; treat volatility management as a later
  challenger, not the primary test.
- **Time-series vs cross-sectional (LIT-025 carry paper and LIT-028 interactions).** The
  refresh reaffirms that crypto momentum is shorter-horizon and that winners-minus-losers
  behavior differs sharply by leg and by liquidity. **Decision:** require separate
  reporting for time-series vs cross-sectional, long-leg vs short-leg, large/liquid vs
  smaller, and spot-long-only vs realistically shortable perpetual implementations.

### Carry (split into separate mechanisms)

- **Crypto Carry (LIT-025, Schmeling/Schrimpf/Todorov 2026, Management Science).** A
  dedicated crypto carry factor (futures basis) is now peer-reviewed and shows economically
  large monthly premia that collapse in stress. This supports splitting `CARRY-01` into
  (a) fixed-expiry futures basis, (b) perpetual funding, (c) staking rewards, and (d)
  token incentives/emissions if studied later — without collapsing them into one generic
  yield factor.
- **Perpetual funding microstructure (LIT-037, Zhivkov 2026, Mathematics).** A two-tiered
  CEX-dominated funding-rate market where most arbitrage spreads vanish after costs.
  Relevant to the perpetual-funding leg and to realistic cost/turnover assumptions.
- **Liquid staking derivatives (LIT-035, Scharnowski & Jahanshahloo 2025, JFM).** First
  economic analysis of the liquid-staking basis and its determinants (staking rewards,
  concentration, limits to arbitrage, sentiment). Supports the staking-rewards leg of
  carry and the need for point-in-time staking-yield histories.

### Token dilution (new candidate DIL-01)

- **Token Dilution and the Cross-Section (LIT-030, Guo 2026, SSRN).** Documents a token
  dilution premium: FDV premium and 12-week dilution rate predict cross-sectional returns
  (t-stats −3.13, −2.79; long-short spreads 25–32% annualized), concentrated in the first
  year of trading and absent in blue-chip/mature coins. This is a working paper (Tier C)
  and the empirical basis for `DIL-01`. **Decision:** add `DIL-01` as `DEFERRED` /
  `UNTESTED`; block empirical testing until point-in-time supply, FDV, unlock-schedule, and
  actual-unlock histories exist.
- **Ethereum tokenomics (LIT-036, Mohammad et al. 2026, Front. Blockchain).** On-chain
  fundamentals (TVL, unlocks, burns, governance concentration) relate to ETH value; unlocks
  show a negative price relationship (β = −0.22, p < 0.001). Reinforces the dilution
  mechanism and the data-audit gate.

### Network value (raise priority, Phase 2)

- **ML high-dimensional factor modeling (LIT-033, Li et al. 2026, PBFJ).** Tree-based ML
  predicts crypto returns; SHAP shows market-to-realized-value, new addresses, and active
  addresses are the most influential predictors. Directly supports `NET-01` candidate
  concepts (active/new addresses, network activity) and the requirement that network-value
  definitions, provider revisions, and availability timestamps be auditable before
  advancement.

### Factor zoo and hidden factors (robustness requirements)

- **Crypto factor zoo (LIT-029, Mercik/Zaremba/Demir 2026, IRFA).** Applying iterative
  alpha-based factor compression to 36 crypto predictors, only 2–3 factors beyond the market
  eliminate all significant alphas; liquidity proxies (turnover volatility, bid-ask spread)
  and blockchain-native metrics (new-address-to-price) dominate. Factor selections are
  temporally unstable. **Implication:** raw long-short returns do not establish independent
  alpha; we must control for accepted crypto factors, broad market exposure, volatility/crash
  exposure, selected traditional factors, and latent PCA/hidden-factor controls.
- **Cross-sectional interactions (LIT-028, Mercik et al. 2025, IRFA).** Liquidity, risk, and
  past-return interactions dominate; equal-weighted OOS Sharpe exceeds 1 but low liquidity
  dampens trading. Supports requiring interaction/regularized-ML challengers only after
  transparent baselines.
- **Crypto Pricing with Hidden Factors (LIT-031, Brigida 2026, arXiv).** Giglio-Xiu
  three-pass latent-factor approach shows crypto returns load on crypto-specific and selected
  equity-industry factors; latent controls materially change estimated premia. Supports the
  hidden-factor control requirement.
- **Q-7 seven-factor model (LIT-032, Babayev & Aliyev 2026, SSRN).** A practitioner seven-factor
  toolkit (market/size/momentum + on-chain quality, value, residual volatility, funding
  sentiment). Declared commercial conflict (QuantNest founder). Recorded as a lead/challenger,
  not established evidence; note the authors report short-term reversal rather than momentum in
  their broader sample — a divergence to investigate, not adopt.

### Costs, capacity, shortability, microstructure

- **DeFi survey (LIT-034, Castillo León & Lehar 2026, JoCF).** Surveys DeFi mechanisms,
  liquidity provision, leverage, fragility, and MEV — context for execution-simulation and
  cost modeling of derivative legs.
- LIT-026, LIT-029, and LIT-037 all confirm that trading frictions materially narrow the set
  of exploitable crypto factors; costs/capacity/shortability enter every promotion gate.

## What was NOT found or not settled

- No 2025–2026 paper resolves the momentum-crash question for crypto (LIT-026 vs LIT-027
  disagree); we therefore require separate crash attribution and both raw and volatility-managed
  reporting.
- No public, point-in-time, history-backed supply/unlock dataset was located; this remains the
  binding constraint for `DIL-01` and is recorded in `06_DATA_FEASIBILITY_BACKLOG.csv`.
- The factor-zoo compression (LIT-029) is itself a 2018–2024 sample; its temporal instability
  argues for out-of-sample, fold-local validation of any baseline we adopt.

## Bottom line for research design

Simple, transparent factor baselines (momentum, liquidity, carry legs, network value) are
retained and specified more strictly. Complex models (CTREND, interactions, ML, hidden-factor
controls) are positioned as challengers that may advance only after the baselines are frozen
and realistic implementation controls exist. `DIL-01` is added as a deferred candidate gated by
a data-audit prerequisite.
