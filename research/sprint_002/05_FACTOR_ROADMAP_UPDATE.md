# 05 — Factor Roadmap Update

**Sprint:** 002
**Supersedes:** Sprint 001 factor roadmap (carried, not edited)

This update converts the 2025–2026 literature into explicit research-design positions for
each factor family. It is a design record, not empirical evidence. No factor is marked
validated.

## MOM-01 — Medium-term momentum (retained, specified stricter)

- Keep the primary simple momentum test (time-series and cross-sectional, weekly).
- **Primary momentum-implementation evidence: LIT-038** (Han/Kang/Ryu, SSRN 4675565,
  revised 26 Mar 2026). Under daily price fluctuations many momentum portfolios are
  liquidated before terminal backtest returns and significant mean returns often turn
  negative; mean-return significance is insufficient; time-series momentum is strong,
  cross-sectional momentum almost non-existent.
- **New required reporting dimensions** (see RD-01):
  - time-series vs cross-sectional;
  - long-leg vs short-leg contribution;
  - large/liquid vs smaller assets;
  - spot long-only vs realistically shortable perpetual implementations;
  - raw vs volatility-managed exposure;
  - ordinary return accounting vs margin/liquidation-aware wealth paths;
  - asset-level concentration and crash attribution;
  - transaction costs and daily mark-to-market wealth paths;
  - explicit margin, futures mechanics, and liquidation assumptions;
  - portfolios treated as liquidatable before terminal backtest returns;
  - separate long/short leg attribution (LIT-038).
- The crypto-carry paper (LIT-025) is NOT used as the principal momentum evidence; it stays
  with CARRY-01 (below).
- **Challengers (after freeze):** CTREND (LIT-024), market-state conditioning, complex
  price-volume combinations (RD-02). Volatility management is a later challenger, not the
  primary test, because LIT-026 and LIT-027 disagree on whether crypto momentum crashes
  exist.

## LIQ-01 — Liquidity (retained, dual role)

- Retain as both (RD-03):
  - a point-in-time eligibility, cost, and capacity input; and
  - a separately evaluated candidate return predictor.
- Require separating liquidity alpha from mechanical universe-selection and cost effects
  (LIT-028, LIT-029).

## CARRY-01 — Perpetual carry (split into mechanisms)

- Split into separately evaluated legs (RD-04):
  1. fixed-expiry futures basis (LIT-025);
  2. perpetual funding (LIT-037, and existing H-004);
  3. staking rewards (LIT-035, LIT-018);
  4. token incentives/emissions, if studied later.
- Do not collapse into one generic yield factor without spanning evidence across legs.

## DIL-01 — Token dilution and unlock pressure (NEW, deferred)

- Added as `DEFERRED` / `UNTESTED` (RD-05). New hypothesis `H-011`.
- Empirical test blocked until point-in-time supply/FDV/unlock/actual-unlock histories pass
  audit (LIT-030, LIT-036; see `06_DATA_FEASIBILITY_BACKLOG.csv`).

## NET-01 — Network and protocol activity (retained, priority raised)

- Keep as Phase 2 but raise priority (RD-06). Candidate concepts from LIT-033/LIT-036:
  active addresses / market cap, new-address growth, transaction activity, protocol
  revenue/fees, MVRV-like measures, network growth, token-function classifications.
- Advance only after definitions, provider revisions, chain mappings, spam/entity effects,
  and availability timestamps are auditable.

## Hidden factors and controls (cross-cutting)

- All factor tests must control for (RD-07): accepted crypto factors, broad crypto market
  exposure, volatility/crash exposure, selected traditional-market factors, latent PCA /
  hidden-factor controls (LIT-029, LIT-031), and token sector / economic-function
  classifications. Raw long-short returns alone do not establish independent alpha.

## Complex models (challengers)

- Factor interactions, regularized ML, shallow nonlinear models, and information-driven bars
  remain challengers (RD-08; LIT-028, LIT-031, LIT-032, LIT-033). Advance only after
  transparent baselines and realistic implementation controls exist.

## Promotion-gate linkage

These design positions feed the Research→Paper and Paper→Live gates in ADR-0008. No
promotion event may be recorded on the basis of a `SUPPORTED`/`REPLICATED` hypothesis
alone; the Promotion Registry authorization is separate (see ADR-0008).
