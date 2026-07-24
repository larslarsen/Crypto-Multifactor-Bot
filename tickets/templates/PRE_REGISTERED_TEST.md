# Pre-Registered Single-Hypothesis Factor Test

**Template version:** 1.0  
**Governance:** ARCH-001 / ADR-0008  
**Rule:** This file must be filled in and committed to `tickets/` before any exploration code is written or run. It must specify exactly one primary hypothesis and one pre-registered decision rule.

---

## 1. Ticket & Authorization

- **Ticket ID:** e.g., `FACTOR-XXX`
- **Authorizing reviewer:**
- **Pre-registration date (UTC):**
- **Effective date / data lock date:**

## 2. Hypothesis

State a single, falsifiable hypothesis in plain language and as a quantitative decision rule.

- **Plain-language hypothesis:**
- **Primary metric:** (e.g., total net return, Sharpe ratio, information ratio)
- **Pre-registered decision rule:**
  - If `metric >= threshold` AND `p-value <= significance_level` on the reserved holdout, the hypothesis is accepted.
  - Otherwise, the hypothesis is rejected and the factor is archived.

## 3. Factor Identity

- **factor_id:**
- **Model artifact ID:**
- **Economic rationale:** (one paragraph)
- **Parameters:**
  - `lookback_days:`
  - `skip_days:`
  - Any other parameters:
- **Parameter freeze:** Confirm that no parameter will be changed after the test begins. ___ (initials)

## 4. Data & Holdout

- **Canonical dataset ID:**
- **Dataset quality status:** (must be PASS or PASS_WITH_WARNINGS)
- **Exploration window:** (must not overlap with the reserved holdout)
- **Reserved holdout window:**
- **Holdout start:**
- **Holdout end:**
- **Holdout contamination check:** Confirm that no prior grid, selection, tuning, or paper session used the holdout window. ___ (initials)

## 5. Universe & Risk Policy

- **Universe:**
- **Venue:**
- **Rebalancing frequency:**
- **Risk policy:**
  - `max_single_weight:`
  - `max_gross_leverage:`
  - `enforcement:`
- **Transaction cost assumptions:**

## 6. Statistical Protocol

- **Significance level (alpha):** (e.g., 0.05)
- **Multiple-testing correction:** (e.g., none, because this is a single pre-registered hypothesis; if any secondary tests are planned, list them here and state they are exploratory)
- **Minimum acceptable return / threshold:**
- **Test statistic / p-value method:** (e.g., block-bootstrap of weekly returns)
- **Sample-size / power note:**

## 7. Pre-Registered Commitments

- [ ] Exactly one primary hypothesis is tested.
- [ ] All parameters are locked before the first backtest.
- [ ] The holdout window was reserved before any analysis began.
- [ ] No data from the holdout window was used in factor design, parameter selection, or prior paper sessions.
- [ ] If the test fails, the factor will be archived (REJECTED or RETIRED) and no post-hoc rescue will be attempted.
- [ ] Any secondary/exploratory analyses will be clearly labeled as such and will not be used to override the primary decision rule.

## 8. Expected Outputs

- Artifact path for the pre-registered test result:
- Stop condition:

## 9. Out of Scope

- LIVE promotion without a separate ticket and owner authority.
- Any use of the contaminated pre-2026-07-24 window for new factor selection.

---

**Signatures / Review:**

- Researcher:
- Reviewer:
- Date:
