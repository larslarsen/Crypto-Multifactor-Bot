# Pre-Registered Single-Hypothesis Factor Test — EXP-009

**Template version:** 1.0
**Governance:** ARCH-001 / ADR-0008 / ADR-0014
**Status:** SIGNED — implementation authorized; prospective outcomes remain sealed.

---

## 1. Ticket & Authorization

- **Ticket ID:** `EXP-009`
- **Authorizing reviewer:** Lead Quantitative Finance Researcher/Engineer (Sol 5.6 High) — **signed**
- **Pre-registration date (UTC):** 2026-07-27
- **Effective date / data lock date:** 2026-07-27T00:00:00Z

## 2. Hypothesis

- **Plain-language hypothesis:** On the survivorship-bound Binance USDT panel, a
  canonical long-horizon time-series momentum signal earns a positive net return after
  costs. This is the first test on a universe whose membership is resolved as-of each
  decision, so it is the first result not confounded by survivorship.

- **Primary metric:** total net return over the reserved holdout, after fees and slippage.

- **Pre-registered decision rule:**
  - **Accept** if `total_net_return >= +0.02` **AND** `p <= 0.05` (one-sided) on the
    reserved holdout.
  - **Otherwise reject**, archive the factor, and attempt no post-hoc rescue.

## 3. Factor Identity

- **factor_id:** `tsmom_365_30`
- **Model artifact ID:** `mod_tsmom_365_30_exp009` (to be registered at run time)
- **Economic rationale:** Time-series momentum at a ~12-month lookback with a ~1-month
  skip is the canonical specification in the academic literature (Moskowitz, Ooi &
  Pedersen 2012). It is adopted here **a priori from that literature**, deliberately
  *not* selected from this repository's prior grids. Every configuration that appeared
  in EXP-004…EXP-008 carries selection contamination: choosing one of them now would be
  a post-hoc rescue of a result ADR-0014 already invalidated. The skip month avoids
  short-horizon reversal contaminating the momentum estimate.
- **Parameters:**
  - `lookback_days:` 365
  - `skip_days:` 30
  - Rebalance: weekly (Friday 00:00 UTC decisions)
- **Parameter freeze:** No parameter may change after the test begins. CO5 / SOL

## 4. Data & Holdout

- **Canonical dataset ID (bars):** `ds_2bf3bf423a0c751e856dad506f12b6d8b4185b01f7408c46d76a9e7eed3f1497` (DATA-011)
- **Dataset quality status:** PASS
- **Universe dataset ID:** `ds_22d2100a575a9764cceec9cc75f45867047969d1b348fd630771bfb083f5b3d8` (UNIVERSE-006)
- **Exploration window:** 2020-01-01 → 2026-07-01 (the full published DATA-011 span)
- **Reserved holdout window:** **prospective only** — decisions strictly after
  **2026-07-27T00:00:00Z**, the data lock date.
- **Holdout start:** 2026-07-31T00:00:00Z
- **Holdout end:** 2027-01-22T00:00:00Z (26 Friday decisions inclusive; not extendable)

### Holdout contamination check — BLOCKING ISSUE, READ BEFORE SIGNING

**A retrospective holdout is not available inside DATA-011 and must not be carved out
of it.** DATA-011 spans 2020-01-01 → 2026-07-01. Prior grid, OOS, full-window and paper
sessions (EXP-004…EXP-008, PAPER-007…PAPER-009) ran on overlapping windows through
2026-07-23. Every in-sample date in the published panel has therefore already been seen
by parameter search or paper execution. Reserving a "holdout" tail of DATA-011 would be
contaminated by construction.

The only uncontaminated window is **forward in time**. This pre-registration therefore
declares a *prospective* holdout beginning after the data lock date. Consequences the
reviewer must accept before signing:

1. EXP-009 cannot produce an accept/reject verdict until ~26 weeks of new bars exist.
2. Any run over the 2020–2026-07 span is **exploratory only** and may not be used to
   accept the hypothesis, tune parameters, or justify promotion.
3. If the reviewer instead wants a verdict sooner, DATA-011 must be extended with data
   after 2026-07-27 and this document re-signed with the concrete dates.

_Confirmed no prior grid, selection, tuning, or paper session used the holdout window
(true by construction — the window does not yet exist)._ CO5 / SOL

## 5. Universe & Risk Policy

- **Universe:** resolved per decision via ARCH-002 `load_paper_universe_binding`:
  `quality_bar_panel_with_coverage(t) minus cmc_dead_at(t)`.
  Policy `quality_bar_panel_minus_cmc_dead_v1`, binding code version `v3`.
  Static maps are venue translation only, never membership.
- **Panel size:** **22 symbols, not 23.** `DOGEUSD` (instrument 11) has no bars in
  DATA-011 in either the `daily/` or `intraday/` tree, contradicting REVIEW-0216's
  "all 23 paper symbols backfilled, 0 excluded". The binding correctly excludes it
  rather than inventing coverage.
- **Membership is time-varying**, so power is not constant across the span:

  | decision time | eligible names |
  |---|---|
  | 2020-06-01 | 7 |
  | 2022-01-01 | 15 |
  | 2024-01-01 | 22 |
  | 2026-06-01 | 22 |

- **Venue:** Binance spot (USDT pairs), paper execution only
- **Rebalancing frequency:** weekly
- **Risk policy:**
  - `max_single_weight:` `MAX_SINGLE_ASSET_WEIGHT` (0.15)
  - `max_gross_leverage:` `MAX_GROSS_LEVERAGE` (1.0)
  - `enforcement:` clip and renormalize, enforced every decision
- **Transaction cost assumptions:** 5 bps fee + 5 bps slippage per side

## 6. Statistical Protocol

- **Significance level (alpha):** 0.05, one-sided
- **Multiple-testing correction:** **None required — exactly one hypothesis is tested.**
  This is the entire point of the ticket. No grid, no config sweep, no "best of N".
  Any secondary analysis is exploratory and cannot override the primary rule.
- **Minimum acceptable return / threshold:** +2.0% net over the holdout
- **Test statistic / p-value method:** stationary block bootstrap of weekly net returns,
  block length 4 weeks, 10,000 resamples, one-sided against H0: mean weekly return <= 0
- **Sample-size / power note:** 26 weekly decisions on <=22 names is a **small sample**.
  Under an optimistic iid approximation with 3% weekly portfolio volatility, one-sided
  alpha 5%, and 80% power, the detectable mean is about 1.46% per week, or roughly 38%
  arithmetic cumulative return over 26 weeks. Four-week blocks reduce effective
  information further. The +2% economic threshold is therefore severely underpowered.
  The reviewer knowingly accepts this as a conservative promotion gate: failure to pass
  archives this factor version but is not evidence that the economic effect is absent.

## 7. Pre-Registered Commitments

- [x] Exactly one primary hypothesis is tested.
- [x] All parameters are locked before the first backtest.
- [x] The holdout window was reserved before any analysis began.
- [x] No data from the holdout window was used in factor design, parameter selection, or prior paper sessions.
- [x] If the test fails, the factor will be archived (REJECTED or RETIRED) and no post-hoc rescue will be attempted.
- [x] Any secondary/exploratory analyses will be clearly labeled as such and will not be used to override the primary decision rule.

## 8. Expected Outputs

- **Artifact path:** `research/sprint_004/42_EXP009_PREREGISTERED_TSMOM.json`
- **Required artifact fields** (ARCH-002 enforced, EXP-009 scope item 3):
  - `universe_dataset_id`, `bar_panel_dataset_id`
  - `universe_binding_series` — the complete ordered per-decision coverage time series,
    one entry per executed decision, validated against each period's decision time
  - `survivorship_policy`, `universe_code_version`
  - `survivorship_invalid: false`
- **Stop condition:** AWAITING_REVIEW. Promotion only via a separate PROMO ticket, and
  only if the holdout passes the pre-registered rule.

## 9. Out of Scope

- LIVE promotion without a separate ticket and owner authority.
- Any use of the contaminated pre-2026-07-24 window for factor selection.
- Re-running prior grids for "confirmation".

---

**Signatures / Review:**

- Researcher: Sr Dev — Claude Opus 5, 2026-07-27
- Reviewer: Sol 5.6 High
- Date: 2026-07-27
