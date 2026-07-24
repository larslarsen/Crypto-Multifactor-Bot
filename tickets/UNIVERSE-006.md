# UNIVERSE-006 — Publish CMC Survivorship + Composite Tradable Membership

**Priority:** P0  
**Status:** AWAITING_REVIEW  
**Dependencies:** ARCH-002 (ACCEPTED), UNIVERSE-003 (ACCEPTED), ADR-0012, ADR-0014  
**Layer:** universe / catalog  
**Architecture:** one-shot CMC CSV → immutable catalog universe dataset; composite
membership = survivorship ∩ bar availability. **No LIVE. No unofficial CMC polling loop.**

## Objective

Turn the existing `data/survivorship/cmc_dead_universe_full.csv` (1,756 rows) into a
**catalog-published** universe dataset and expose production `universe_at(t)` via
UniverseBinding, including intersection with instruments that have quality bars.

## Scope

### In scope

1. Publish registry as catalog dataset type `universe_membership` (or existing universe type).
2. `CMCSurvivorshipProvider` loads from catalog/dataset path, not only loose CSV.
3. **Composite provider:** `alive_at(t) ∩ has_quality_bars_asof(t) ∩ optional_screen`.
4. Provenance fields preserved (`death_date_is_proxy`, `source=cmc_data_api_unofficial`).
5. Evidence report `research/sprint_004/42_CMC_UNIVERSE_PUBLISHED.json` with row counts,
   date coverage, sample as-of membership sizes.

### Out of scope

- Fetching CMC again (re-use file; re-fetch only if regenerating one-shot with documented reason)
- Factor experiments
- DEX

## Acceptance (Jr)

1. Catalog contains universe dataset with ≥1,500 rows  
2. `universe_at(2020-01-01)` and `universe_at(2026-07-01)` return different sizes (sanity)  
3. pytest universe + control check PASS  

## Stop Condition

After Sr: AWAITING_REVIEW. Next: NONE (then DATA-011).
