# 07 — Open Research Questions

**Sprint:** 002
**Research cutoff:** 2026-07-18

Open questions raised or sharpened by the 2025–2026 refresh. None are answered here; they
are pointers for future design and for the data-feasibility backlog (`06`).

1. **Do crypto momentum crashes exist, and where?** LIT-026 (Yang 2025) finds crypto lacks
   extended momentum crashes and that volatility management raises returns; LIT-027 (Grobys
   et al. 2025) documents severe crashes in large-cap equal-weighted momentum and endorses
   volatility management for mitigation. Which finding holds under our universe, costs, and
   shortability assumptions? Requires separate crash attribution (RD-01).

2. **Which carry mechanism actually prices, and with what data?** LIT-025 establishes a
   futures-basis carry; LIT-035 a liquid-staking basis; LIT-037 a fragmented funding-rate
   market where most arbitrage vanishes after costs. Can the three legs be measured with
   point-in-time, audit-passing data, and do they load on distinct risks (RD-04)?

3. **Is the dilution premium real and implementable?** LIT-030 reports a strong,
   new-coin-concentrated dilution premium, but only with point-in-time supply/unlock data
   we do not yet have (DF-01, DF-02). Does the effect survive a supply/FDV history that is
   knowable on each decision date, net of costs, and outside the first trading year
   (RD-05)?

4. **Which network-value metric is point-in-time auditable?** LIT-033 shows new/active
   addresses are influential; LIT-036 shows on-chain fundamentals relate to ETH value. But
   provider revisions, chain mappings, spam/entity effects, and availability timestamps must
   be auditable before NET-01 advances (RD-06).

5. **How many crypto factors are real, and are they stable?** LIT-029 compresses 36 predictors
   to 2–3 beyond market, dominated by liquidity and blockchain-native metrics, but selections
   are temporally unstable. Which baseline set should we preregister, and how do we validate it
   out-of-sample across folds without overfitting (RD-07)?

6. **Do latent/hidden factors bias our premia?** LIT-031 shows latent controls materially
   change estimated crypto premia. Should every factor test include a PCA/hidden-factor
   control, and at what lag/horizon (RD-07)?

7. **Do complex models add value net of costs?** LIT-028/LIT-033 show ML/interaction gains,
   but they are liquidity- and cost-dependent and LIT-032 is a conflicted practitioner lead.
   Under what fold-local, costed design do interactions/ML beat transparent baselines (RD-08)?

8. **Reversal vs momentum in the broad recent sample.** LIT-032 reports short-term reversal
   rather than momentum in a 90-token 2020–2026 sample, diverging from Liu et al. (2022). Is
   this a sample/era effect, a definition difference, or a real regime change we must design
   for?
